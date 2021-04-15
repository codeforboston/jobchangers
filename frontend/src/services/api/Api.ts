import { Occupation } from '../../domain/occupation';
import { State } from '../../domain/state';
import { Transition } from '../../domain/transition';

export type GetTransitionRequest = {
  state?: State;
  sourceOccupation: Occupation;
};

export default interface Api {
  getOccupations: (request: string) => Promise<Occupation[]>;

  getStates: () => Promise<State[]>;

  getTransitions: (request: GetTransitionRequest) => Promise<Transition[]>;
}
