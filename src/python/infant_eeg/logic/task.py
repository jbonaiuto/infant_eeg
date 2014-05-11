from PySide import QtCore
import copy
import random
from infant_eeg.logic.settings import EffectorSettings
from infant_eeg.logic.state import *
from infant_eeg.logic.target import *

class Task(QtCore.QObject):

    textDataChanged=QtCore.Signal(object)
    booleanDataChanged=QtCore.Signal(object)

    def __init__(self, id, name):
        QtCore.QObject.__init__(self)
        self.myWin=None
        self.inputManager=None
        self.outputManager=None
        self.id=id
        self.name=name
        self.init_state=None
        self.init_states=[]
        self.effector_settings=None
        self.states={}
        self.target_generator=None

    def get_init_state(self):
        if self.init_state=='random':
            return random.choice(self.init_states)
        else:
            return self.init_state

    @classmethod
    def new_from_file(cls, task_element, win, inputManager, outputManager):

        task=Task(None, task_element.attrib['name'])
        task.myWin=win
        task.inputManager=inputManager
        task.outputManager=outputManager

        task.init_state=task_element.find('init_state').text
        if task.init_state=='random':
            random_elem=task_element.find('random_init_states')
            init_state_list=random_elem.findall('init_state')
            task.init_states=[]
            for state_node in init_state_list:
                task.init_states.append(state_node.text)

        effector_node=task_element.find('effector_settings')
        if effector_node is not None:
            task.effector_settings=EffectorSettings(effector_node, win)

        state_list=task_element.find('states').findall('state')
        for idx,state_node in enumerate(state_list):
            name=state_node.attrib['name']
            type_name=state_node.attrib['type']
            if type_name=='acquire':
                task.states[name]=AcquireState(idx,task.myWin, name, task.inputManager, task.outputManager,
                    task.effector_settings, state_node)
            elif type_name=='effector_dissociation_acquire':
                task.states[name]=EffectorDissociationAcquireState(idx,task.myWin, name, task.inputManager,
                    task.outputManager, task.effector_settings, state_node)
            elif type_name=='dual_acquire':
                task.states[name]=DualAcquireState(idx,task.myWin, name, task.inputManager, task.outputManager,
                    task.effector_settings, state_node)
            elif type_name=='effector_dissociation_dual_acquire':
                task.states[name]=EffectorDissociationDualAcquireState(idx,task.myWin, name, task.inputManager, task.outputManager,
                    task.effector_settings, state_node)
            elif type_name=='hold':
                task.states[name]=HoldState(idx,task.myWin, name, task.inputManager, task.outputManager,
                    task.effector_settings, state_node)
            elif type_name=='dual_hold':
                task.states[name]=DualHoldState(idx,task.myWin, name, task.inputManager, task.outputManager,
                    task.effector_settings, state_node)
            elif type_name=='effector_dissociation_dual_hold':
                task.states[name]=EffectorDissociationDualHoldState(idx,task.myWin, name, task.inputManager, task.outputManager,
                    task.effector_settings, state_node)
            elif type_name=='effector_dissociation_hold':
                task.states[name]=EffectorDissociationHoldState(idx,task.myWin, name, task.inputManager,
                    task.outputManager, task.effector_settings, state_node)
            elif type_name=='cue':
                task.states[name]=CueState(idx,task.myWin, name, task.inputManager, task.outputManager,
                    task.effector_settings, state_node)
            elif type_name=='dual_cue':
                task.states[name]=DualCueState(idx,task.myWin, name, task.inputManager, task.outputManager,
                    task.effector_settings, state_node)
            elif type_name=='effector_dissociation_dual_cue':
                task.states[name]=EffectorDissociationDualCueState(idx,task.myWin, name, task.inputManager, task.outputManager,
                    task.effector_settings, state_node)
            elif type_name=='effector_dissociation_cue':
                task.states[name]=EffectorDissociationCueState(idx,task.myWin, name, task.inputManager, task.outputManager,
                    task.effector_settings, state_node)
            elif type_name=='memory':
                task.states[name]=MemoryState(idx,task.myWin, name, task.inputManager, task.outputManager,
                    task.effector_settings, state_node)
            elif type_name=='effector_dissociation_memory':
                task.states[name]=EffectorDissociationMemoryState(idx,task.myWin, name, task.inputManager, task.outputManager,
                    task.effector_settings, state_node)
            elif type_name=='reward':
                task.states[name]=RewardState(idx,task.myWin, name, task.inputManager, task.outputManager,
                    task.effector_settings, state_node)
            elif type_name=='interval':
                task.states[name]=IntervalState(idx,task.myWin, name, task.inputManager, task.outputManager,
                    task.effector_settings, state_node)
            elif type_name=='movie':
                task.states[name]=MovieState(idx,task.myWin, name, task.inputManager, task.outputManager,
                    task.effector_settings, state_node)
            elif type_name=='test_joystick':
                task.states[name]=TestJoystickState(idx,task.myWin, name, task.inputManager, task.outputManager,
                    task.effector_settings, state_node)

        generator_node=task_element.find('target_generator')
        if generator_node is not None:
            if generator_node.attrib['type']=='dynamic':
                task.target_generator=DynamicTargetGenerator(generator_node)
            elif generator_node.attrib['type']=='static':
                task.target_generator=StaticTargetGenerator(generator_node)
            elif generator_node.attrib['type']=='dual_static':
                task.target_generator=DualStaticTargetGenerator(generator_node)

        return task

    def save(self, file):
        file.write('<task name="%s">\n' % self.name)
        file.write('<init_state>%s</init_state>\n' % self.init_state)
        if self.init_state=='random':
            file.write('<random_init_states>\n')
            for init_state in self.init_states:
                file.write('<init_state>%s</init_state>\n' % init_state)
            file.write('</random_init_states>\n')
        file.write(self.effector_settings.get_xml())
        if self.target_generator is not None:
            file.write(self.target_generator.get_xml())
        file.write('<states>\n')
        sorted_states=sorted(self.states.iteritems(), key=lambda x: x[1].order)
        for name, state in sorted_states:
            file.write(state.get_xml())
        file.write('</states>\n')
        file.write('</task>\n')
        file.close()

    def init_trial(self, logger, run_info):
        # Set target position
        run_info.dual_trial=False
        if self.target_generator is not None:
            targets=self.target_generator.get_current_target()
            for target_name, target in targets.iteritems():
                logger.info('target:%s:(%.4f,%.4f)' % (target_name, target[0], target[1]))
                for state_name in self.target_generator.params['states_to_update'].selected_options:
                    from_units=self.target_generator.params['units'].value
                    to_units=self.states[state_name].param_groups['target'].params['units'].value
                    conv_target=copy.copy(target)
                    conv_target=convert_position(conv_target, from_units, to_units, self.myWin)
                    self.states[state_name].set_position(target_name, conv_target)
            if len(targets)>0:
                t=targets['target']
                if 'target_prime' in targets:
                    t_prime=targets['target_prime']
                    if (not t[0]==t_prime[0]) or (not t[1]==t_prime[1]):
                        run_info.dual_trial=True

        init_state=self.get_init_state()
        self.states[init_state].initialize(run_info)
        return init_state

    def iter_trial(self):
        if self.target_generator is not None:
            self.target_generator.iter_trial()
