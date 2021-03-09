from .models import Socs, BlsOes, StateAbbPairs, OccupationTransitions, SocDescription
from rest_framework import viewsets, permissions, generics
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from django.forms.models import model_to_dict
from collections import namedtuple
import django_filters
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.pagination import LimitOffsetPagination
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, Any
from decouple import config
from .serializers import (
    BlsOesSerializer,
    StateNamesSerializer,
    SocListSerializer,
    OccupationTransitionsSerializer,
    BlsTransitionsSerializer,
)
import logging

log = logging.getLogger()


# Documentation for Django generally refers to these views as views.py rather than api.py

class BlsOesFilter(django_filters.FilterSet):
    """
    Create a filter to use with the BlsOes model. When multiple options are chosen in these filters, there
    must be no space between comma-separated values
    """
    socs = django_filters.BaseInFilter(field_name='soc_code', lookup_expr='in')
    areas = django_filters.BaseInFilter(field_name='area_title', lookup_expr='in')

    class Meta:
        model = BlsOes
        fields = ['socs', 'areas']


class BlsOesViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for wage/employment data by location, SOC code, and year
    """
    queryset = BlsOes.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = BlsOesSerializer
    throttle_classes = [AnonRateThrottle]
    pagination_class = LimitOffsetPagination
    filter_class = BlsOesFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class SocListFilter(django_filters.FilterSet):
    """
    Create a filter to use with the BlsOes model. When multiple options are chosen in these filters, there
    must be no space between comma-separated values. min_transition_observations refers to the minimum number of
    observations used to derive transition probabilities for a given source SOC. According to Schubert, Stansbury,
    and Taska (2020), this need not be an integer since it can be reweighted by age.
    """
    socs = django_filters.BaseInFilter(field_name="soc_code", lookup_expr="in")
    min_transition_observations = django_filters.NumberFilter(field_name="total_transition_obs", lookup_expr="gte")

    class Meta:
        model = SocDescription
        fields = ["socs", "min_transition_observations"]


class SocListSimpleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for all unique SOC codes and descriptions with wage/employment data available
    """
    queryset = SocDescription.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = SocListSerializer
    throttle_classes = [AnonRateThrottle]
    filter_class = SocListFilter


class SocListSmartViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for finding SOC codes matching a user's requested keyword
    """
    serializer_class = SocListSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    DEFAULT_ONET_LIMIT = 10
    MAX_ONET_LIMIT = 50

    DEFAULT_OBS_LIMIT = 1000

    # Include a manual parameter that can be included in the request query (+ swagger_auto_schema decorator)
    KEYWORD_PARAMETER = openapi.Parameter("keyword_search",
                                          openapi.IN_QUERY,
                                          description="Keyword search via O*NET",
                                          type=openapi.TYPE_STRING)
    ONET_LIMIT_PARAMETER = openapi.Parameter("onet_limit",
                                             openapi.IN_QUERY,
                                             description=f"Limit to O*NET search results",
                                             type=openapi.TYPE_INTEGER)

    OBS_LIMIT_PARAM = openapi.Parameter("min_weighted_obs",
                                        openapi.IN_QUERY,
                                        description="Minimum (weighted) observed transitions from source SOC",
                                        type=openapi.TYPE_NUMBER)

    def _set_params(self, request):
        """
        Set parameters based on the request. Custom parameters are identified by their openapi.Parameter name

        :param request: User-input parameters
        :return: Relevant parameters from the request
        """
        self.keyword_search = request.query_params.get("keyword_search")
        self.onet_limit = request.query_params.get("onet_limit")
        self.obs_limit = request.query_params.get("min_weighted_obs")

        if not self.onet_limit or int(self.onet_limit) > self.MAX_ONET_LIMIT:
            self.onet_limit = self.DEFAULT_ONET_LIMIT
        if not self.obs_limit:
            self.obs_limit = self.DEFAULT_OBS_LIMIT

    def get_queryset(self):
        """
        Custom queryset used that is a combination of querysets from a couple models. Overwriting to prevent
        schema generation warning.
        """
        pass

    @staticmethod
    def search_onet_keyword(keyword: str,
                            limit: int = 20) -> Dict[str, Any]:
        """
        Search for a keyword that will be matched to SOC codes via the O*Net API

        :param keyword: Keyword that's requested (user search)
        :param limit: Limit to number of results (should expose this as a parameter)
        :return: JSON response, e.g. {'keyword': 'doctor', ...
                                      'career': [{'href': '',
                                                'code': '29-1216.00',
                                                'title': 'General Internal Medicine Physicians',
                                                'tags': {'bright_outlook': ...},
                                      ...]}
        """
        headers = {"Accept": "application/json"}
        username = config("ONET_USERNAME")
        password = config("ONET_PASSWORD")
        try:
            response = requests.get(f"https://services.onetcenter.org/ws/mnm/search?keyword={keyword}",
                                    headers=headers,
                                    params={'end': limit},
                                    auth=HTTPBasicAuth(username, password))

            return response.json()

        except Exception as e:
            log.warning(e)
            return None

    @swagger_auto_schema(manual_parameters=[KEYWORD_PARAMETER, ONET_LIMIT_PARAMETER, OBS_LIMIT_PARAM])
    def list(self, request):
        """
        Query parameters:
        ------------------------
        * keyword_search: User-input keyword search for related professions
        * onet_limit: Limit to the number of results pulled back from O*NET; capped by MAX_ONET_LIMIT. Responses will
            only include smart-search SOCs with transitions data available. If no response is found from O*NET, all
            available SOC codes are returned.
        * min_weighted_obs: Minimum number of observed transitions (weighted) for a response to be included
        """
        # Parameters are pulled from request query, as defined by openapi.Parameter
        self._set_params(request=request)

        # Django QuerySet with all objects in the SocDescription model
        # model_to_dict serializes each object in the model into a JSON/dict
        available_socs = (SocDescription
                          .objects
                          .filter(total_transition_obs__gte=self.obs_limit))
        available_socs = [model_to_dict(item)
                          for item in available_socs]
        available_soc_codes = [soc.get("soc_code", "") for soc in available_socs]
        available_soc_codes = set(available_soc_codes)

        # Query for O*NET Socs
        onet_soc_codes = None
        if self.keyword_search:
            try:
                onet_socs = self.search_onet_keyword(keyword=self.keyword_search,
                                                     limit=self.onet_limit)
                log.info(f"Smart search results: {onet_socs}")
                onet_soc_codes = onet_socs.get("career")
                onet_soc_codes = [soc.get("code", "") for soc in onet_soc_codes]
                onet_soc_codes = set([soc.split(".")[0] for soc in onet_soc_codes])
                log.info(f"Smart search SOC codes: {onet_soc_codes}")
            except Exception as e:
                log.info(f"Unable to find search results from O*NET for keyword {self.keyword_search} | {e}")

        # Combine O*NET and available transition SOCs to return a response
        if not onet_soc_codes:
            return Response(available_socs)

        smart_soc_codes = list(onet_soc_codes.intersection(available_soc_codes))
        smart_socs = [soc for soc in available_socs
                      if soc.get("soc_code") in smart_soc_codes]

        return Response(smart_socs)


class StateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for states
    """
    queryset = StateAbbPairs.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = StateNamesSerializer
    throttle_classes = [AnonRateThrottle]


class OccupationTransitionsFilter(django_filters.FilterSet):
    """
    Create a filter to use with the OccupationTransitions model in the Occupation Transitions viewset
    """
    # field_name instead of name, and lookup_expr instead of lookup_type is used for the NumberFilter for Django 2.0+
    min_transition_probability = django_filters.NumberFilter(field_name="pi", lookup_expr="gte")

    class Meta:
        model = OccupationTransitions
        fields = ["min_transition_probability", "soc1"]


class OccupationTransitionsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for occupation transitions (burning glass) data
    """
    queryset = OccupationTransitions.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = OccupationTransitionsSerializer
    throttle_classes = [AnonRateThrottle]
    pagination_class = LimitOffsetPagination
    filter_class = OccupationTransitionsFilter


class BlsTransitionsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A custom ViewSet for BLS OES wage/employment data and occupation transitions/burning glass data
    See Swagger docs for more details on the GET endpoint /transitions-extended/.
    /transitions-extended/{id}/ is not supported.
    Sample endpoint query:
    ------------------------
    /?area_title=Massachusetts&soc=35-3031&min_transitions_probability=0.01
    """
    serializer_class = BlsTransitionsSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]
    # swagger_schema = None         # Exclude from swagger schema.

    # Use a named tuple to pass data from multiple models to the response
    BLS_TRANSITIONS = namedtuple("BlsTransitions", ("bls", "transitions"))

    DEFAULT_AREA = "U.S."
    DEFAULT_SOC = "35-3031"         # 35-3031 is waiters and waitresses
    DEFAULT_TRANSITION_PROBABILITY = 0.01
    SOC_SWAGGER_PARAM = openapi.Parameter("soc",
                                          openapi.IN_QUERY,
                                          description="Source SOC code",
                                          type=openapi.TYPE_STRING)
    AREA_SWAGGER_PARAM = openapi.Parameter("area_title",
                                           openapi.IN_QUERY,
                                           description="Location",
                                           type=openapi.TYPE_STRING)
    PI_SWAGGER_PARAM = openapi.Parameter("min_transition_probability",
                                         openapi.IN_QUERY,
                                         description="Minimum transition probability",
                                         type=openapi.TYPE_NUMBER
                                         )

    def get_queryset(self):
        """
        Custom queryset used that is a combination of querysets from a couple models. Overwriting to prevent
        schema generation warning.
        """
        pass

    def _set_params(self, request):
        """
        Set parameters based on the request. Custom parameters are identified by their openapi.Parameter name

        :param request: User-input parameters
        :return: Relevant parameters from the request
        """
        area_title = request.query_params.get("area_title")
        source_soc = request.query_params.get("soc")
        min_transition_probability = request.query_params.get("min_transition_probability")

        if not area_title:
            self.area_title_filter = self.DEFAULT_AREA
        else:
            self.area_title_filter = area_title
        if not source_soc:
            self.source_soc = self.DEFAULT_SOC
        else:
            self.source_soc = source_soc
        if not min_transition_probability:
            self.min_transition_probability = self.DEFAULT_TRANSITION_PROBABILITY
        else:
            self.min_transition_probability = min_transition_probability

    @swagger_auto_schema(manual_parameters=[SOC_SWAGGER_PARAM, PI_SWAGGER_PARAM, AREA_SWAGGER_PARAM])
    def list(self, request):
        """
        Query parameters:
        ------------------------
        * area_title: Specify an area_title to return wages/employment for that location only
        States should be fully spelled out, consistent with the area_title field in the
        BlsOes model. The default is specified by DEFAULT_AREA
        * soc: Specify a source SOC code to return transitions data for people moving from this
        occupation to other occupations. The default is specified by DEFAULT_SOC
        * min_transition_probability: Specify the minimum transitions probability. Do not return any
        transitions records that have a probability of moving from SOC1 to SOC2 that is lower
        than this value.
        Multiple selections are not supported for this endpoint. The default response is displayed.
        Sample endpoint query:
        ------------------------
        * /?area_title=Massachusetts&soc=11-1011&min_transitions_probability=0.01
        Response format:
        ------------------------
        {"source_soc": {
            "source_soc_id": 242047,
            "source_soc_area_title": "U.S.",
            "source_soc_soc_code": "13-2011",
            "source_soc_soc_title": "Accountants and Auditors",
            "source_soc_hourly_mean_wage": 38.23,
            "source_soc_annual_mean_wage": 79520,
            "source_soc_total_employment": 1280700,
            "source_soc_soc_decimal_code": "13-2011.00",
            "source_soc_file_year": 2019
          },
        "transition_rows": [
            {
              "id": 1,
              "soc1": "13-2011",
              "soc2": "11-3031",
              "pi": 0.1782961,
              "total_transition_obs": 390865.6,
              "soc2_id": 241905,
              "soc2_area_title": "U.S.",
              "soc2_soc_code": "11-3031",
              "soc2_soc_title": "Financial Managers",
              "soc2_hourly_mean_wage": 70.93,
              "soc2_annual_mean_wage": 147530,
              "soc2_total_employment": 654790,
              "soc2_soc_decimal_code": "11-3031.00",
              "soc2_file_year": 2019
            },
        """
        self._set_params(request)

        bls_transitions = self.BLS_TRANSITIONS(
            bls=(BlsOes.objects
                 .filter(area_title=self.area_title_filter)),
            transitions=(OccupationTransitions.objects
                         .filter(soc1=self.source_soc)
                         .filter(pi__gte=self.min_transition_probability)
                         ),
            )

        # Convert bls_transitions QuerySet to dicts & join the results
        # List of dicts, each containing metadata on SOCs and transitions
        bls = [model_to_dict(item)
               for item in bls_transitions[0]]
        transitions = [model_to_dict(item, exclude=["occleaveshare", "total_soc"])
                       for item in bls_transitions[1]]

        source_soc_info = [item
                           for item in bls
                           if item.get("soc_code") == self.source_soc]
        source_soc_info = [{f"source_soc_{key}": val
                            for key, val in record.items()}
                           for record in source_soc_info]
        assert len(source_soc_info) <= 1, "Duplicate SOC wage/employment data found in BlsOes model for this location!"
        if source_soc_info:
            source_soc_info = source_soc_info[0]

        destination_socs = [item.get("soc2") for item in transitions]

        destination_soc_map = {}
        for item in bls:
            if item.get("soc_code") in destination_socs:
                destination_soc_map.update({item.get("soc_code"): item})

        for transition in transitions:
            destination_soc = transition.get("soc2")
            destination_metadata = destination_soc_map.get(destination_soc)
            if destination_metadata:
                destination_metadata = {f"soc2_{key}": val
                                        for key, val in destination_metadata.items()}
                transition.update(destination_metadata)

        # Alternative for simple response that just lists the results from each model:
        #   serializer = BlsTransitionsSerializer(bls_transitions)
        #   return Response(serializer.data)
        return Response({
            "source_soc":  source_soc_info,
            "transition_rows": transitions,
        })
