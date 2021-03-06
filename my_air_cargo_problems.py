from aimacode.logic import PropKB
from aimacode.planning import Action
from aimacode.search import (
    Node, Problem,
)
from aimacode.utils import expr
from lp_utils import (
    FluentState, encode_state, decode_state,
)
from my_planning_graph import PlanningGraph


class AirCargoProblem(Problem):
    def __init__(self, cargos, planes, airports, initial: FluentState, goal: list):
        """

        :param cargos: list of str
            cargos in the problem
        :param planes: list of str
            planes in the problem
        :param airports: list of str
            airports in the problem
        :param initial: FluentState object
            positive and negative literal fluents (as expr) describing initial state
        :param goal: list of expr
            literal fluents required for goal test
        """
        self.state_map = initial.pos + initial.neg
        self.initial_state_TF = encode_state(initial, self.state_map)
        Problem.__init__(self, self.initial_state_TF, goal=goal)
        self.cargos = cargos
        self.planes = planes
        self.airports = airports
        self.actions_list = self.get_actions()

    def get_actions(self):
        '''
        This method creates concrete actions (no variables) for all actions in the problem
        domain action schema and turns them into complete Action objects as defined in the
        aimacode.planning module. It is computationally expensive to call this method directly;
        however, it is called in the constructor and the results cached in the `actions_list` property.

        Returns:
        ----------
        list<Action>
            list of Action objects
        '''

        # TODO create concrete Action objects based on the domain action schema for: Load, Unload, and Fly
        # concrete actions definition: specific literal action that does not include variables as with the schema
        # for example, the action schema 'Load(c, p, a)' can represent the concrete actions 'Load(C1, P1, SFO)'
        # or 'Load(C2, P2, JFK)'.  The actions for the planning problem must be concrete because the problems in
        # forward search and Planning Graphs must use Propositional Logic

        def load_actions():
            '''Create all concrete Load actions and return a list

            :return: list of Action objects
            '''
            loads = []
            for ap in self.airports:
                for p in self.planes:
                    for c in self.cargos:
                        precond_pos = [expr("At({}, {})".format(p, ap)),
                                       expr("At({}, {})".format(c, ap))
                                       ]
                        precond_neg = [expr("In({}, {})".format(c, p))]

                        effect_add = [expr("In({}, {})".format(c, p))]
                        effect_rem = [expr("At({}, {})".format(c, ap))]
                        load = Action(expr("Load({}, {})".format(c, p)), [precond_pos, precond_neg],
                                      [effect_add, effect_rem])
                        loads.append(load)
            return loads

        def unload_actions():
            '''Create all concrete Unload actions and return a list

            :return: list of Action objects
            '''
            unloads = []
            for ap in self.airports:
                for p in self.planes:
                    for c in self.cargos:
                        precond_pos = [expr("In({}, {})".format(c, p)),
                                       expr("At({}, {})".format(p, ap))
                                       ]
                        precond_neg = [expr("At({}, {})".format(c, ap))]

                        effect_add = [expr("At({}, {})".format(c, ap))]
                        effect_rem = [expr("In({}, {})".format(c, p))]
                        unload = Action(expr("Unload({}, {})".format(c, p)), [precond_pos, precond_neg],
                                        [effect_add, effect_rem])
                        unloads.append(unload)
            return unloads

        def fly_actions():
            '''Create all concrete Fly actions and return a list

            :return: list of Action objects
            '''
            flys = []
            for fr in self.airports:
                for to in self.airports:
                    if fr != to:
                        for p in self.planes:
                            precond_pos = [expr("At({}, {})".format(p, fr)),
                                           ]
                            precond_neg = []
                            effect_add = [expr("At({}, {})".format(p, to))]
                            effect_rem = [expr("At({}, {})".format(p, fr))]
                            fly = Action(expr("Fly({}, {}, {})".format(p, fr, to)),
                                         [precond_pos, precond_neg],
                                         [effect_add, effect_rem])
                            flys.append(fly)
            return flys

        return load_actions() + unload_actions() + fly_actions()

    def actions(self, state: str) -> list:
        """ Return the actions that can be executed in the given state.

        :param state: str
            state represented as T/F string of mapped fluents (state variables)
            e.g. 'FTTTFF'
        :return: list of Action objects
        """
        possible_actions = []
        fluents = decode_state(state, self.state_map)
        fluents_pos_set = set(fluents.pos)
        fluents_neg_set = set(fluents.neg)
        for a in self.actions_list:
            a_pos_set = set(a.precond_pos)
            a_neg_set = set(a.precond_neg)
            if a_neg_set.issubset(fluents_neg_set) and a_pos_set.issubset(fluents_pos_set):
                possible_actions.append(a)
        return possible_actions

    def result(self, state: str, action: Action):
        """ Return the state that results from executing the given
        action in the given state. The action must be one of
        self.actions(state).

        :param state: state entering node
        :param action: Action applied
        :return: resulting state after action
        """
        fluents = decode_state(state, self.state_map)
        pos_list = [x for x in fluents.pos if x not in action.effect_rem] + action.effect_add
        neg_list = [x for x in fluents.neg if x not in action.effect_add] + action.effect_rem
        new_state = FluentState(pos_list, neg_list)
        return encode_state(new_state, self.state_map)

    def goal_test(self, state: str) -> bool:
        """ Test the state to see if goal is reached

        :param state: str representing state
        :return: bool
        """
        kb = PropKB()
        kb.tell(decode_state(state, self.state_map).pos_sentence())
        for clause in self.goal:
            if clause not in kb.clauses:
                return False
        return True

    def h_1(self, node: Node):
        # note that this is not a true heuristic
        h_const = 1
        return h_const

    def h_pg_levelsum(self, node: Node):
        '''
        This heuristic uses a planning graph representation of the problem
        state space to estimate the sum of all actions that must be carried
        out from the current state in order to satisfy each individual goal
        condition.
        '''
        # requires implemented PlanningGraph class
        pg = PlanningGraph(self, node.state)
        pg_levelsum = pg.h_levelsum()
        return pg_levelsum

    def h_ignore_preconditions(self, node: Node):
        '''
        This heuristic estimates the minimum number of actions that must be
        carried out from the current state in order to satisfy all of the goal
        conditions by ignoring the preconditions required for an action to be
        executed.
        '''
        count = 0
        x = decode_state(node.state, self.state_map)
        for g in self.goal:
            if g in x.neg:
                count += 1
        return count


def air_cargo_p1() -> AirCargoProblem:
    cargoes = ['C1', 'C2']
    planes = ['P1', 'P2']
    airports = ['JFK', 'SFO']
    pos = [expr('At(C1, SFO)'),
           expr('At(C2, JFK)'),
           expr('At(P1, SFO)'),
           expr('At(P2, JFK)'),
           ]
    neg = [expr('At(C2, SFO)'),
           expr('In(C2, P1)'),
           expr('In(C2, P2)'),
           expr('At(C1, JFK)'),
           expr('In(C1, P1)'),
           expr('In(C1, P2)'),
           expr('At(P1, JFK)'),
           expr('At(P2, SFO)'),
           ]
    init = FluentState(pos, neg)
    goal = [expr('At(C1, JFK)'),
            expr('At(C2, SFO)'),
            ]
    return AirCargoProblem(cargoes, planes, airports, init, goal)


def air_cargo_p2() -> AirCargoProblem:
    airports = ['SFO', 'JFK', 'ATL']
    return formulate_problem(airports, 3, 3)


def air_cargo_p3() -> AirCargoProblem:
    airports = ['SFO', 'JFK', 'ATL', 'ORD']
    return formulate_problem(airports, 4, 2)


def formulate_problem(airports, c, p):
    cargoes = ['C' + str(x+1) for x in range(c)]
    planes = ['P' + str(x+1) for x in range(p)]
    pos = []
    neg = []
    goal = []
    for c in cargoes:
        for p in planes:
            neg.append(expr('In({}, {})'.format(c, p)))
    for ia, a in enumerate(airports):
        for ic, c in enumerate(cargoes):
            e = expr('At({}, {})'.format(c, a))
            if ia == ic:
                pos.append(e)
            else:
                neg.append(e)
            if ic == len(airports) - ia - 1:
                goal.append(expr('At({}, {})'.format(c, a)))

        for ip, p in enumerate(planes):
            e1 = expr('At({}, {})'.format(p, a))
            if ip == ia:
                pos.append(e1)
            else:
                neg.append(e1)
    init = FluentState(pos, neg)
    return AirCargoProblem(cargoes, planes, airports, init, goal)
