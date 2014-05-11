import copy
import random
import numpy as np
from psychopy import visual
from infant_eeg.logic.param import ParamContainingObject
from infant_eeg.util import get_vertex_list, convert_color_to_psychopy, convert_position, convert_size, get_dist


class State(ParamContainingObject):

    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        ParamContainingObject.__init__(self, name, state_node, required_params=required_params,
            required_param_groups=required_param_groups)
        self.window=win
        self.order=order
        self.in_manager=in_manager
        self.out_manager=out_manager
        self.effector_settings=effector_settings
        self.eye_pos=None
        if self.window is not None:
            self.init_stimulus()

    def init_stimulus(self):
        pass

    # Initialize a target stimulus based on its parameter values
    def init_target_stimulus(self, stim_name):
        aspect = 1.0
        if self.param_groups[stim_name].params['units'].value == 'norm':
            aspect = float(self.window.size[0]) / float(self.window.size[1])
        vertex_list = get_vertex_list(self.param_groups[stim_name].params['radius'].value,
            self.param_groups[stim_name].params['num_vertices'].value, aspect)
        color = convert_color_to_psychopy((self.param_groups[stim_name].params['red'].value,
                                           self.param_groups[stim_name].params['green'].value,
                                           self.param_groups[stim_name].params['blue'].value))
        stim = visual.ShapeStim(self.window, fillColor=color, lineColor=color, vertices=vertex_list,
            pos=(self.param_groups[stim_name].params['position'].x_value,
                 self.param_groups[stim_name].params['position'].y_value),
            opacity=self.param_groups[stim_name].params['alpha'].value,
            units=self.param_groups[stim_name].params['units'].value)

        return aspect, stim

    def initialize(self, run_info):
        self.state_started=-1

    def get_xml(self):
        xml='<state name="%s" type=""/>\n' % self.name
        xml+=self.get_inner_xml()
        xml+='</state>\n'
        return xml

    def run(self, t, visual_info, run_info, logger):
        if self.state_started<0:
            self.state_started=t
            logger.info('state:%s' % self.name)

        # Show eye position
        if 'eye' in self.effector_settings.param_groups:
            self.eye_pos=copy.copy(self.in_manager.read('eye'))

        # Show hand position
        if 'hand' in self.effector_settings.param_groups:
            self.hand_pos=copy.copy(self.in_manager.read('hand'))

        return self.name

    def get_effector_dist(self, effector, position, units):
        aspect=float(self.window.size[0])/float(self.window.size[1])
        if effector=='eye':
            norm_pos=convert_position(position,units,'norm',self.window)
            return get_dist(self.eye_pos, norm_pos, aspect=aspect)
        elif effector=='hand':
            norm_pos=convert_position(position,units,'norm',self.window)
            return get_dist(self.hand_pos, norm_pos, aspect=aspect)
        return None

    def effector_within_tolerance(self, position, tolerance, units):
        tolerance_norm=convert_size(tolerance, units, 'norm', self.window)
        effector_control=self.effector_settings.params['effector_control'].value
        if effector_control=='eye_only':
            dist=self.get_effector_dist('eye',position,units)
            return dist<=tolerance_norm
        elif effector_control=='hand_only':
            dist=self.get_effector_dist('hand',position,units)
            return dist<=tolerance_norm
        elif effector_control=='eye_and_hand':
            eye_dist=self.get_effector_dist('eye',position,units)
            hand_dist=self.get_effector_dist('hand',position,units)
            return eye_dist<=tolerance_norm >= hand_dist
        return True

    def effector_within_tolerance_multiple(self, fixation_position, target_position, fixation_tolerance,
                                           target_tolerance, fixation_units, target_units):
        fixation_tolerance_norm=convert_size(fixation_tolerance, fixation_units, 'norm', self.window)
        target_tolerance_norm=convert_size(target_tolerance, target_units, 'norm', self.window)
        window_constraint=self.effector_settings.params['window_constraint'].value
        effector_control=self.effector_settings.params['effector_control'].value
        if effector_control=='eye_and_hand':
            if window_constraint=='eye_only':
                fixation_dist=self.get_effector_dist('eye',fixation_position,fixation_units)
                target_dist=self.get_effector_dist('hand',target_position,target_units)
                return fixation_dist<=fixation_tolerance_norm and target_dist<=target_tolerance_norm
            elif window_constraint=='hand_only':
                fixation_dist=self.get_effector_dist('hand',fixation_position,fixation_units)
                target_dist=self.get_effector_dist('eye',target_position,target_units)
                return fixation_dist<=fixation_tolerance_norm and target_dist<=target_tolerance_norm
        return True

    def effector_within_tolerance_fixation(self, position, tolerance, units):
        tolerance_norm=convert_size(tolerance, units, 'norm', self.window)
        window_constraint=self.effector_settings.params['window_constraint'].value
        effector_control=self.effector_settings.params['effector_control'].value
        if effector_control=='eye_and_hand':
            if window_constraint=='eye_only':
                fixation_dist=self.get_effector_dist('eye',position,units)
                return fixation_dist<=tolerance_norm
            elif window_constraint=='hand_only':
                fixation_dist=self.get_effector_dist('hand',position,units)
                return fixation_dist<=tolerance_norm
        return True

    def abort_motion(self, check_motion, check_lick):
        if check_motion and 'motion' in self.in_manager.input_names and self.in_manager.read('motion')<1:
            motion_error_color=convert_color_to_psychopy((self.param_groups['motion_error_color'].params['red'].value,
                                                          self.param_groups['motion_error_color'].params['green'].value,
                                                          self.param_groups['motion_error_color'].params['blue'].value))
            self.window.setColor(motion_error_color)
            return True
        elif check_lick and 'lick' in self.in_manager.input_names and self.in_manager.read('lick')<1:
            lick_error_color=convert_color_to_psychopy((self.param_groups['lick_error_color'].params['red'].value,
                                                        self.param_groups['lick_error_color'].params['green'].value,
                                                        self.param_groups['lick_error_color'].params['blue'].value))
            self.window.setColor(lick_error_color)
            return True
        return False


class MovieState(State):

    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.extend(['duration','success_next_state'])
        required_param_groups['video']=['file']
        State.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

        self.video_stim=None

    def initialize(self, run_info):
        State.initialize(self, run_info)
        if self.video_stim is None:
            self.video_stim=visual.MovieStim(self.window, self.param_groups['video'].params['file'].path,
                size=(self.window.size[0],self.window.size[1]))
        else:
            self.video_stim.loadMovie(self.param_groups['video'].params['file'].path)
        self.paused=False

    def get_xml(self):
        xml='<state name="%s" type="movie">\n' % self.name
        xml+=self.get_inner_xml()
        xml+='</state>\n'
        return xml

    def run(self, t, visual_info, run_info, logger):
        next_state=State.run(self, t, visual_info, run_info, logger)

        if self.video_stim is not None:
            if t==self.state_started:
                self.video_stim.seek(0)
            if not self.paused and self.video_stim.status==visual.FINISHED:
                next_state=self.params['success_next_state'].value
            else:
                self.video_stim.draw()
        return next_state


class SingleTargetState(State):

    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.extend(['duration','success_next_state','fail_next_state'])
        required_param_groups['target']=['show','units','position','radius','tolerance','num_vertices','red',
                                         'green','blue','alpha']
        State.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

    def init_stimulus(self):
        State.init_stimulus(self)

        self.aspect,self.target_stim=self.init_target_stimulus('target')

    def run(self, t, visual_info, run_info, logger):
        next_state=State.run(self, t, visual_info, run_info, logger)

        style='dash'
        if self.param_groups['target'].params['show'].value:
            style='solid'
            self.target_stim.draw()

        visual_info.stimuli['%s-target' % self.name] =self.update_target_stim_info('target')
        return next_state

    def set_position(self, group_name, pos):
        self.param_groups[group_name].params['position'].x_value=pos[0]
        self.param_groups[group_name].params['position'].y_value=pos[1]
        if group_name=='target':
            self.target_stim.setPos(pos)
        p_tuple=(group_name,'position',pos)
        self.groupPositionDataChanged.emit(p_tuple)

class DualTargetState(SingleTargetState):

    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        self.target_prime_stim=None
        SingleTargetState.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

    def init_stimulus(self):
        SingleTargetState.init_stimulus(self)

        pos=(self.param_groups['target'].params['position'].x_value,
             self.param_groups['target'].params['position'].y_value)
        if self.target_prime_stim is not None:
            pos=self.target_prime_stim.pos
        self.aspect,self.target_prime_stim=self.init_target_stimulus('target')
        self.target_prime_stim.setPos(pos)

    def run(self, t, visual_info, run_info, logger):
        next_state=SingleTargetState.run(self, t, visual_info, run_info, logger)

        if self.param_groups['target'].params['show'].value:
            self.target_prime_stim.draw()

        visual_info.stimuli['%s-target_prime' % self.name]=self.update_target_stim_info('target')
        units=self.param_groups['target'].params['units'].value
        visual_info.stimuli['%s-target_prime' % self.name].position=convert_position(self.target_prime_stim.pos,units,
            'norm',self.window)
        return next_state

    def set_position(self, group_name, pos):
        if group_name=='target':
            self.param_groups[group_name].params['position'].x_value=pos[0]
            self.param_groups[group_name].params['position'].y_value=pos[1]
            self.target_stim.setPos(pos)
            p_tuple=(group_name,'position',pos)
            self.groupPositionDataChanged.emit(p_tuple)
        elif group_name=='target_prime':
            self.target_prime_stim.setPos(pos)

class FixationTargetState(SingleTargetState):
    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_param_groups['fixation']=['show','units','position','radius','tolerance','num_vertices','red',
                                           'green','blue','alpha']
        SingleTargetState.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

    def init_stimulus(self):
        SingleTargetState.init_stimulus(self)

        self.f_aspect,self.fixation_stim=self.init_target_stimulus('fixation')

    def run(self, t, visual_info, run_info, logger):
        next_state=SingleTargetState.run(self, t, visual_info, run_info, logger)

        if self.param_groups['fixation'].params['show'].value:
            self.fixation_stim.draw()

        visual_info.stimuli['%s-fixation' % self.name]=self.update_target_stim_info('fixation')

        return next_state

    def set_position(self, group_name, pos):
        SingleTargetState.set_position(self, group_name, pos)
        if group_name=='fixation':
            self.fixation_stim.setPos(pos)

class AcquireState(SingleTargetState):

    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.append('check_lick')
        required_param_groups['lick_error_color']=['red','green','blue']
        SingleTargetState.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)


    def get_xml(self):
        xml_str='<state name="%s" type="acquire">\n' % self.name
        xml_str+=self.get_inner_xml()
        xml_str+='</state>\n'
        return xml_str

    def run(self, t, visual_info, run_info, logger):
        next_state=SingleTargetState.run(self, t, visual_info, run_info, logger)

        if self.effector_within_tolerance((self.param_groups['target'].params['position'].x_value,
                                           self.param_groups['target'].params['position'].y_value),
            self.param_groups['target'].params['tolerance'].value,
            self.param_groups['target'].params['units'].value):
            next_state=self.params['success_next_state'].value
        elif t>self.state_started+self.params['duration'].value:
            next_state=self.params['fail_next_state'].value
            run_info.last_state=self.name

        if self.abort_motion(False, self.params['check_lick'].value):
            return self.params['fail_next_state'].value

        return next_state

class DualAcquireState(DualTargetState):

    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.append('check_lick')
        required_param_groups['lick_error_color']=['red','green','blue']
        DualTargetState.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

    def initialize(self, run_info):
        DualTargetState.initialize(self, run_info)

    def get_xml(self):
        xml_str='<state name="%s" type="dual_acquire">\n' % self.name
        xml_str+=self.get_inner_xml()
        xml_str+='</state>\n'
        return xml_str

    def run(self, t, visual_info, run_info, logger):
        next_state=DualTargetState.run(self, t, visual_info, run_info, logger)

        t_selected=self.effector_within_tolerance(self.target_stim.pos,
            self.param_groups['target'].params['tolerance'].value,self.param_groups['target'].params['units'].value)
        tp_selected=self.effector_within_tolerance(self.target_prime_stim.pos,
            self.param_groups['target'].params['tolerance'].value,self.param_groups['target'].params['units'].value)

        if t_selected or tp_selected:
            next_state=self.params['success_next_state'].value
            if get_dist(self.target_stim.pos,self.target_prime_stim.pos)>.01:
                if (t_selected and self.target_stim.pos[0]<0) or (tp_selected and self.target_prime_stim.pos[0]<0):
                    run_info.increment_choice('left')
                else:
                    run_info.increment_choice('right')
        elif t>self.state_started+self.params['duration'].value:
            next_state=self.params['fail_next_state'].value
            run_info.last_state=self.name

        if self.abort_motion(False, self.params['check_lick'].value):
            return self.params['fail_next_state'].value

        return next_state

class EffectorDissociationDualAcquireState(DualAcquireState):
    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.extend(['blink_tolerance','saccade_tolerance','check_lick'])
        required_param_groups['effector_error_color']=['red','green','blue']
        required_param_groups['fixation']=['show','units','position','radius','tolerance','num_vertices','red',
                                           'green','blue','alpha']
        required_param_groups['lick_error_color']=['red','green','blue']
        DualTargetState.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)


    def get_xml(self):
        xml_str='<state name="%s" type="effector_dissociation_dual_acquire">\n' % self.name
        xml_str+=self.get_inner_xml()
        xml_str+='</state>\n'
        return xml_str

    def initialize(self, run_info):
        DualAcquireState.initialize(self, run_info)
        self.blink_started=-1

    def init_stimulus(self):
        DualAcquireState.init_stimulus(self)
        self.f_aspect,self.fixation_stim=self.init_target_stimulus('fixation')

    def run(self, t, visual_info, run_info, logger):
        next_state=DualTargetState.run(self, t, visual_info, run_info, logger)

        if self.param_groups['fixation'].params['show'].value:
            self.fixation_stim.draw()

        visual_info.stimuli['%s-fixation' % self.name]=self.update_target_stim_info('fixation')

        # Currently looking away
        if self.blink_started>=0:
            # Looked away too long - end trial
            if t>self.blink_started+self.params['saccade_tolerance'].value:
                self.window.setColor((-1,-1,-1))
                run_info.last_state=self.name
                return self.params['fail_next_state'].value
            # Looking away, not blinking - reset hold timer
            elif t>self.blink_started+self.params['blink_tolerance'].value:
                self.target_acquired=-1

        fixation_pos=(self.param_groups['fixation'].params['position'].x_value,
                      self.param_groups['fixation'].params['position'].y_value)
        target_tolerance=self.param_groups['target'].params['tolerance'].value
        fixation_tolerance=self.param_groups['fixation'].params['tolerance'].value
        target_units=self.param_groups['target'].params['units'].value
        fixation_units=self.param_groups['fixation'].params['units'].value
        if self.effector_within_tolerance_multiple(fixation_pos, self.target_stim.pos, fixation_tolerance,
            target_tolerance, fixation_units, target_units):
            if get_dist(self.target_stim.pos,self.target_prime_stim.pos)>.01:
                if self.target_stim.pos[0]<0:
                    run_info.increment_choice('left')
                else:
                    run_info.increment_choice('right')
            self.window.setColor((-1,-1,-1))
            next_state=self.params['success_next_state'].value
        elif self.effector_within_tolerance_multiple(fixation_pos, self.target_prime_stim.pos, fixation_tolerance,
            target_tolerance, fixation_units, target_units):
            if get_dist(self.target_stim.pos,self.target_prime_stim.pos)>.01:
                if self.target_prime_stim.pos[0]<0:
                    run_info.increment_choice('left')
                else:
                    run_info.increment_choice('right')
            self.window.setColor((-1,-1,-1))
            next_state=self.params['success_next_state'].value
        elif t>self.state_started+self.params['duration'].value:
            next_state=self.params['fail_next_state'].value
            run_info.last_state=self.name
        elif not self.effector_within_tolerance_fixation(fixation_pos, fixation_tolerance, fixation_units):
            self.window.setColor(convert_color_to_psychopy((self.param_groups['effector_error_color'].params['red'].value,
                                                            self.param_groups['effector_error_color'].params['green'].value,
                                                            self.param_groups['effector_error_color'].params['blue'].value)))
            if self.blink_started<0:
                self.blink_started=t

        if self.abort_motion(False, self.params['check_lick'].value):
            return self.params['fail_next_state'].value

        return next_state

class HoldState(SingleTargetState):

    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.extend(['variability','blink_tolerance','saccade_tolerance','check_motion','check_lick'])
        required_param_groups['effector_error_color']=['red','green','blue']
        required_param_groups['motion_error_color']=['red','green','blue']
        required_param_groups['lick_error_color']=['red','green','blue']
        SingleTargetState.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)


    def get_xml(self):
        xml_str='<state name="%s" type="hold">\n' % self.name
        xml_str+=self.get_inner_xml()
        xml_str+='</state>\n'
        return xml_str

    def initialize(self, run_info):
        SingleTargetState.initialize(self, run_info)
        self.target_acquired=-1
        self.blink_started=-1
        self.set_actual_duration(int(self.params['duration'].value+random.random()*self.params['variability'].value))

    def run(self, t, visual_info, run_info, logger):
        next_state=SingleTargetState.run(self, t, visual_info, run_info, logger)

        # Currently looking away
        if self.blink_started>=0:
            # Looked away too long - end trial
            if t>self.blink_started+self.params['saccade_tolerance'].value:
                self.window.setColor((-1,-1,-1))
                run_info.last_state=self.name
                return self.params['fail_next_state'].value
            # Looking away, not blinking - reset hold timer
            elif t>self.blink_started+self.params['blink_tolerance'].value:
                self.target_acquired=-1

        # Finished holding
        elif self.target_acquired>=0 and t>self.target_acquired+self.actual_duration:
            return self.params['success_next_state'].value


        # Holding
        if self.effector_within_tolerance((self.param_groups['target'].params['position'].x_value,
                                           self.param_groups['target'].params['position'].y_value),
            self.param_groups['target'].params['tolerance'].value,
            self.param_groups['target'].params['units'].value):
            self.window.setColor((-1,-1,-1))
            if self.target_acquired<0:
                self.target_acquired=t
            self.blink_started=-1
        # Looking away
        else:
            self.window.setColor(convert_color_to_psychopy((self.param_groups['effector_error_color'].params['red'].value,
                                                            self.param_groups['effector_error_color'].params['green'].value,
                                                            self.param_groups['effector_error_color'].params['blue'].value)))
            if self.blink_started<0:
                self.blink_started=t

        if self.abort_motion(self.params['check_motion'].value, self.params['check_lick'].value):
            return self.params['fail_next_state'].value

        return next_state

    def set_actual_duration(self, d, update_tab=True):
        self.actual_duration=d
        if update_tab:
            self.tab.actual_duration.setText(str(self.actual_duration))
            self.tab.actual_duration.resize(self.tab.actual_duration.sizeHint())

class DualHoldState(DualTargetState):
    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.extend(['variability','blink_tolerance', 'saccade_tolerance','check_motion','check_lick'])
        required_param_groups['effector_error_color']=['red','green','blue']
        required_param_groups['motion_error_color']=['red','green','blue']
        required_param_groups['lick_error_color']=['red','green','blue']
        DualTargetState.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

    def get_xml(self):
        xml_str='<state name="%s" type="dual_hold">\n' % self.name
        xml_str+=self.get_inner_xml()
        xml_str+='</state>\n'
        return xml_str

    def initialize(self, run_info):
        DualTargetState.initialize(self, run_info)
        self.target_acquired=-1
        self.blink_started=-1
        self.set_actual_duration(int(self.params['duration'].value+random.random()*self.params['variability'].value))

    def run(self, t, visual_info, run_info, logger):
        next_state=DualTargetState.run(self, t, visual_info, run_info, logger)

        if self.blink_started>=0:
            if t>self.blink_started+self.params['saccade_tolerance'].value:
                self.window.setColor((-1,-1,-1))
                run_info.last_state=self.name
                return self.params['fail_next_state'].value
            # Looking away, not blinking - reset hold timer
            elif t>self.blink_started+self.params['blink_tolerance'].value:
                self.target_acquired=-1
        elif self.target_acquired>=0 and t>self.target_acquired+self.actual_duration:
            return self.params['success_next_state'].value

        t_selected=self.effector_within_tolerance(self.target_stim.pos,
            self.param_groups['target'].params['tolerance'].value,self.param_groups['target'].params['units'].value)
        tp_selected=self.effector_within_tolerance(self.target_prime_stim.pos,
            self.param_groups['target'].params['tolerance'].value,self.param_groups['target'].params['units'].value)

        if t_selected or tp_selected:
            self.window.setColor((-1,-1,-1))
            if self.target_acquired<0:
                self.target_acquired=t
            self.blink_started=-1
        else:
            self.window.setColor(convert_color_to_psychopy((self.param_groups['effector_error_color'].params['red'].value,
                                                            self.param_groups['effector_error_color'].params['green'].value,
                                                            self.param_groups['effector_error_color'].params['blue'].value)))
            if self.blink_started<0:
                self.blink_started=t

        if self.abort_motion(self.params['check_motion'].value, self.params['check_lick'].value):
            return self.params['fail_next_state'].value

        return next_state

    def set_actual_duration(self, d, update_tab=True):
        self.actual_duration=d
        if update_tab:
            self.tab.actual_duration.setText(str(self.actual_duration))
            self.tab.actual_duration.resize(self.tab.actual_duration.sizeHint())


class EffectorDissociationDualHoldState(DualHoldState):
    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.extend(['variability','blink_tolerance', 'saccade_tolerance','check_motion','check_lick'])
        required_param_groups['effector_error_color']=['red','green','blue']
        required_param_groups['motion_error_color']=['red','green','blue']
        required_param_groups['lick_error_color']=['red','green','blue']
        required_param_groups['fixation']=['show','units','position','radius','tolerance','num_vertices','red',
                                           'green','blue','alpha']
        DualHoldState.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

    def get_xml(self):
        xml_str='<state name="%s" type="effector_dissociation_dual_hold">\n' % self.name
        xml_str+=self.get_inner_xml()
        xml_str+='</state>\n'
        return xml_str

    def init_stimulus(self):
        DualHoldState.init_stimulus(self)

        self.f_aspect, self.fixation_stim=self.init_target_stimulus('fixation')

    def run(self, t, visual_info, run_info, logger):
        next_state=DualTargetState.run(self, t, visual_info, run_info, logger)

        if self.param_groups['fixation'].params['show'].value:
            self.fixation_stim.draw()

        visual_info.stimuli['%s-fixation' % self.name]=self.update_target_stim_info('fixation')

        if self.blink_started>=0:
            if t>self.blink_started+self.params['saccade_tolerance'].value:
                self.window.setColor((-1,-1,-1))
                run_info.last_state=self.name
                return self.params['fail_next_state'].value
            # Looking away, not blinking - reset hold timer
            elif t>self.blink_started+self.params['blink_tolerance'].value:
                self.target_acquired=-1
        elif self.target_acquired>=0 and t>self.target_acquired+self.actual_duration:
            return self.params['success_next_state'].value

        fixation_pos=(self.param_groups['fixation'].params['position'].x_value,
                      self.param_groups['fixation'].params['position'].y_value)
        target_tolerance=self.param_groups['target'].params['tolerance'].value
        fixation_tolerance=self.param_groups['fixation'].params['tolerance'].value
        target_units=self.param_groups['target'].params['units'].value
        fixation_units=self.param_groups['fixation'].params['units'].value
        if self.effector_within_tolerance_multiple(fixation_pos, self.target_stim.pos, fixation_tolerance,
            target_tolerance, fixation_units, target_units):
            self.window.setColor((-1,-1,-1))
            if self.target_acquired<0:
                self.target_acquired=t
            self.blink_started=-1
        elif self.effector_within_tolerance_multiple(fixation_pos, self.target_prime_stim.pos, fixation_tolerance,
            target_tolerance, fixation_units, target_units):
            self.window.setColor((-1,-1,-1))
            if self.target_acquired<0:
                self.target_acquired=t
            self.blink_started=-1
        else:
            self.window.setColor(convert_color_to_psychopy((self.param_groups['effector_error_color'].params['red'].value,
                                                            self.param_groups['effector_error_color'].params['green'].value,
                                                            self.param_groups['effector_error_color'].params['blue'].value)))
            if self.blink_started<0:
                self.blink_started=t

        if self.abort_motion(self.params['check_motion'].value, self.params['check_lick'].value):
            return self.params['fail_next_state'].value
            #if self.blink_started<0:
            #    self.blink_started=t

        return next_state


class DualCueState(DualTargetState):
    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.extend(['blink_tolerance','saccade_tolerance','check_motion','check_lick'])
        required_param_groups['effector_error_color']=['red','green','blue']
        required_param_groups['motion_error_color']=['red','green','blue']
        required_param_groups['lick_error_color']=['red','green','blue']
        required_param_groups['fixation']=['show','units','position','radius','tolerance','num_vertices','red',
                                           'green','blue','alpha']
        DualTargetState.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

    def get_xml(self):
        xml_str='<state name="%s" type="dual_cue">\n' % self.name
        xml_str+=self.get_inner_xml()
        xml_str+='</state>\n'
        return xml_str

    def initialize(self, run_info):
        DualTargetState.initialize(self, run_info)
        self.target_acquired=-1
        self.blink_started=-1

    def init_stimulus(self):
        DualTargetState.init_stimulus(self)

        self.f_aspect,self.fixation_stim=self.init_target_stimulus('fixation')

    def run(self, t, visual_info, run_info, logger):
        next_state=DualTargetState.run(self, t, visual_info, run_info, logger)

        if self.param_groups['fixation'].params['show'].value:
            self.fixation_stim.draw()

        visual_info.stimuli['%s-fixation']=self.update_target_stim_info('fixation')

        if self.blink_started>=0:
            if t>self.blink_started+self.params['saccade_tolerance'].value:
                self.window.setColor((-1,-1,-1))
                run_info.last_state=self.name
                return self.params['fail_next_state'].value
            elif t>self.blink_started+self.params['blink_tolerance'].value:
                self.target_acquired=-1
        elif self.target_acquired>=0 and t>self.target_acquired+self.params['duration'].value:
            return self.params['success_next_state'].value

        if self.effector_within_tolerance((self.param_groups['fixation'].params['position'].x_value,
                                           self.param_groups['fixation'].params['position'].y_value),
            self.param_groups['fixation'].params['tolerance'].value,
            self.param_groups['fixation'].params['units'].value):
            self.window.setColor((-1,-1,-1))
            if self.target_acquired<0:
                self.target_acquired=t
            self.blink_started=-1
        else:
            self.window.setColor(convert_color_to_psychopy((self.param_groups['effector_error_color'].params['red'].value,
                                                            self.param_groups['effector_error_color'].params['green'].value,
                                                            self.param_groups['effector_error_color'].params['blue'].value)))
            if self.blink_started<0:
                self.blink_started=t

        if self.abort_motion(self.params['check_motion'].value, self.params['check_lick'].value):
            return self.params['fail_next_state'].value
            #if self.blink_started<0:
            #    self.blink_started=t

        return next_state


class EffectorDissociationDualCueState(DualCueState):
    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.extend(['blink_tolerance','saccade_tolerance','check_motion','check_lick'])
        required_param_groups['effector_error_color']=['red','green','blue']
        required_param_groups['motion_error_color']=['red','green','blue']
        required_param_groups['lick_error_color']=['red','green','blue']
        required_param_groups['second_fixation']=['show','units','position','radius','tolerance','num_vertices','red',
                                                  'green','blue','alpha']
        DualCueState.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

    def get_xml(self):
        xml_str='<state name="%s" type="effector_dissociation_dual_cue">\n' % self.name
        xml_str+=self.get_inner_xml()
        xml_str+='</state>\n'
        return xml_str

    def initialize(self, run_info):
        DualCueState.initialize(self, run_info)
        self.target_acquired=-1
        self.blink_started=-1

    def init_stimulus(self):
        DualCueState.init_stimulus(self)

        self.f2_aspect,self.second_fixation_stim=self.init_target_stimulus('second_fixation')

    def run(self, t, visual_info, run_info, logger):
        if self.param_groups['second_fixation'].params['show'].value:
            self.second_fixation_stim.draw()

        next_state=DualCueState.run(self, t, visual_info, run_info, logger)

        visual_info.stimuli['%s-second_fixation' % self.name]=self.update_target_stim_info('second_fixation')

        if self.blink_started>=0:
            if t>self.blink_started+self.params['saccade_tolerance'].value:
                self.window.setColor((-1,-1,-1))
                run_info.last_state=self.name
                return self.params['fail_next_state'].value
            elif t>self.blink_started+self.params['blink_tolerance'].value:
                self.target_acquired=-1
        elif self.target_acquired>=0 and t>self.target_acquired+self.params['duration'].value:
            return self.params['success_next_state'].value

        first_fixation_pos=(self.param_groups['fixation'].params['position'].x_value,
                            self.param_groups['fixation'].params['position'].y_value)
        second_fixation_pos=(self.param_groups['second_fixation'].params['position'].x_value,
                             self.param_groups['second_fixation'].params['position'].y_value)
        if self.effector_within_tolerance_multiple(first_fixation_pos, second_fixation_pos,
            self.param_groups['fixation'].params['tolerance'].value,
            self.param_groups['second_fixation'].params['tolerance'].value,
            self.param_groups['fixation'].params['units'].value,
            self.param_groups['second_fixation'].params['units'].value):
            self.window.setColor((-1,-1,-1))
            if self.target_acquired<0:
                self.target_acquired=t
            self.blink_started=-1
        else:
            self.window.setColor(convert_color_to_psychopy((self.param_groups['effector_error_color'].params['red'].value,
                                                            self.param_groups['effector_error_color'].params['green'].value,
                                                            self.param_groups['effector_error_color'].params['blue'].value)))
            if self.blink_started<0:
                self.blink_started=t

        if self.abort_motion(self.params['check_motion'].value, self.params['check_lick'].value):
            return self.params['fail_next_state'].value
            #if self.blink_started<0:
            #    self.blink_started=t

        return next_state

class IntervalState(State):

    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.extend(['duration','success_next_state','check_motion','check_lick'])
        State.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

    def get_xml(self):
        xml_str='<state name="%s" type="interval">\n' % self.name
        xml_str+=self.get_inner_xml()
        xml_str+='</state>\n'
        return xml_str

    def run(self, t, visual_info, run_info, logger):
        next_state=State.run(self, t, visual_info, run_info, logger)
        self.window.setColor((-1,-1,-1))

        if t>self.state_started+self.params['duration'].value:
            return self.params['success_next_state'].value

        if self.abort_motion(self.params['check_motion'].value, self.params['check_lick'].value):
            self.state_started=t

        return next_state


class EffectorDissociationAcquireState(FixationTargetState):
    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.extend(['blink_tolerance','saccade_tolerance','check_lick'])
        required_param_groups['effector_error_color']=['red','green','blue']
        required_param_groups['lick_error_color']=['red','green','blue']
        FixationTargetState.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

    def get_xml(self):
        xml_str='<state name="%s" type="effector_dissociation_acquire">\n' % self.name
        xml_str+=self.get_inner_xml()
        xml_str+='</state>\n'
        return xml_str

    def initialize(self, run_info):
        FixationTargetState.initialize(self, run_info)
        self.blink_started=-1

    def run(self, t, visual_info, run_info, logger):
        next_state=FixationTargetState.run(self, t, visual_info, run_info, logger)

        # Currently looking away
        if self.blink_started>=0:
            # Looked away too long - end trial
            if t>self.blink_started+self.params['saccade_tolerance'].value:
                self.window.setColor((-1,-1,-1))
                run_info.last_state=self.name
                return self.params['fail_next_state'].value
            # Looking away, not blinking - reset hold timer
            elif t>self.blink_started+self.params['blink_tolerance'].value:
                self.target_acquired=-1

        target_pos=(self.param_groups['target'].params['position'].x_value,
                    self.param_groups['target'].params['position'].y_value)
        fixation_pos=(self.param_groups['fixation'].params['position'].x_value,
                      self.param_groups['fixation'].params['position'].y_value)
        target_tolerance=self.param_groups['target'].params['tolerance'].value
        fixation_tolerance=self.param_groups['fixation'].params['tolerance'].value
        target_units=self.param_groups['target'].params['units'].value
        fixation_units=self.param_groups['fixation'].params['units'].value
        if self.effector_within_tolerance_multiple(fixation_pos, target_pos, fixation_tolerance, target_tolerance,
            fixation_units, target_units):
            self.window.setColor((-1,-1,-1))
            next_state=self.params['success_next_state'].value
        elif t>self.state_started+self.params['duration'].value:
            next_state=self.params['fail_next_state'].value
            run_info.last_state=self.name
        elif not self.effector_within_tolerance_fixation(fixation_pos, fixation_tolerance, fixation_units):
            self.window.setColor(convert_color_to_psychopy((self.param_groups['effector_error_color'].params['red'].value,
                                                            self.param_groups['effector_error_color'].params['green'].value,
                                                            self.param_groups['effector_error_color'].params['blue'].value)))
            if self.blink_started<0:
                self.blink_started=t

        if self.abort_motion(False, self.params['check_lick'].value):
            return self.params['fail_next_state'].value

        return next_state


class EffectorDissociationHoldState(FixationTargetState):

    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.extend(['variability','blink_tolerance','saccade_tolerance','check_motion','check_lick'])
        required_param_groups['effector_error_color']=['red','green','blue']
        required_param_groups['motion_error_color']=['red','green','blue']
        required_param_groups['lick_error_color']=['red','green','blue']
        FixationTargetState.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

    def get_xml(self):
        xml_str='<state name="%s" type="effector_dissociation_hold">\n' % self.name
        xml_str+=self.get_inner_xml()
        xml_str+='</state>\n'
        return xml_str

    def initialize(self, run_info):
        FixationTargetState.initialize(self, run_info)
        self.target_acquired=-1
        self.blink_started=-1
        self.set_actual_duration(int(self.params['duration'].value+random.random()*self.params['variability'].value))

    def run(self, t, visual_info, run_info, logger):
        next_state=FixationTargetState.run(self, t, visual_info, run_info, logger)

        # Currently looking away
        if self.blink_started>=0:
            # Looked away too long - end trial
            if t>self.blink_started+self.params['saccade_tolerance'].value:
                self.window.setColor((-1,-1,-1))
                run_info.last_state=self.name
                return self.params['fail_next_state'].value
            # Looking away, not blinking - reset hold timer
            elif t>self.blink_started+self.params['blink_tolerance'].value:
                self.target_acquired=-1

        # Finished holding
        elif self.target_acquired>=0 and t>self.target_acquired+self.actual_duration:
            return self.params['success_next_state'].value


        # Holding
        fixation_pos=(self.param_groups['fixation'].params['position'].x_value,
                      self.param_groups['fixation'].params['position'].y_value)
        target_pos=(self.param_groups['target'].params['position'].x_value,
                    self.param_groups['target'].params['position'].y_value)
        if self.effector_within_tolerance_multiple(fixation_pos, target_pos,
            self.param_groups['fixation'].params['tolerance'].value,
            self.param_groups['target'].params['tolerance'].value,
            self.param_groups['fixation'].params['units'].value,
            self.param_groups['target'].params['units'].value):
            self.window.setColor((-1,-1,-1))
            if self.target_acquired<0:
                self.target_acquired=t
            self.blink_started=-1
        # Looking away
        else:
            self.window.setColor(convert_color_to_psychopy((self.param_groups['effector_error_color'].params['red'].value,
                                                            self.param_groups['effector_error_color'].params['green'].value,
                                                            self.param_groups['effector_error_color'].params['blue'].value)))
            if self.blink_started<0:
                self.blink_started=t

        if self.abort_motion(self.params['check_motion'].value, self.params['check_lick'].value):
            return self.params['fail_next_state'].value
            #if self.blink_started<0:
            #    self.blink_started=t

        return next_state

    def set_actual_duration(self, d, update_tab=True):
        self.actual_duration=d
        if update_tab:
            self.tab.actual_duration.setText(str(self.actual_duration))
            self.tab.actual_duration.resize(self.tab.actual_duration.sizeHint())

class CueState(FixationTargetState):

    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.extend(['blink_tolerance','saccade_tolerance','check_motion','check_lick'])
        required_param_groups['effector_error_color']=['red','green','blue']
        required_param_groups['motion_error_color']=['red','green','blue']
        required_param_groups['lick_error_color']=['red','green','blue']
        FixationTargetState.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

    def get_xml(self):
        xml_str='<state name="%s" type="cue">\n' % self.name
        xml_str+=self.get_inner_xml()
        xml_str+='</state>\n'
        return xml_str

    def initialize(self, run_info):
        FixationTargetState.initialize(self, run_info)
        self.target_acquired=-1
        self.blink_started=-1

    def run(self, t, visual_info, run_info, logger):
        next_state=FixationTargetState.run(self, t, visual_info, run_info, logger)

        if self.blink_started>=0:
            if t>self.blink_started+self.params['saccade_tolerance'].value:
                self.window.setColor((-1,-1,-1))
                run_info.last_state=self.name
                return self.params['fail_next_state'].value
            elif t>self.blink_started+self.params['blink_tolerance'].value:
                self.target_acquired=-1
        elif self.target_acquired>=0 and t>self.target_acquired+self.params['duration'].value:
            return self.params['success_next_state'].value

        if self.effector_within_tolerance((self.param_groups['fixation'].params['position'].x_value,
                                           self.param_groups['fixation'].params['position'].y_value),
            self.param_groups['fixation'].params['tolerance'].value,
            self.param_groups['fixation'].params['units'].value):
            self.window.setColor((-1,-1,-1))
            if self.target_acquired<0:
                self.target_acquired=t
            self.blink_started=-1
        else:
            self.window.setColor(convert_color_to_psychopy((self.param_groups['effector_error_color'].params['red'].value,
                                                            self.param_groups['effector_error_color'].params['green'].value,
                                                            self.param_groups['effector_error_color'].params['blue'].value)))
            if self.blink_started<0:
                self.blink_started=t

        if self.abort_motion(self.params['check_motion'].value, self.params['check_lick'].value):
            return self.params['fail_next_state'].value
            #if self.blink_started<0:
            #    self.blink_started=t

        return next_state


class EffectorDissociationCueState(CueState):
    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.extend(['blink_tolerance','saccade_tolerance','check_motion','check_lick'])
        required_param_groups['effector_error_color']=['red','green','blue']
        required_param_groups['motion_error_color']=['red','green','blue']
        required_param_groups['lick_error_color']=['red','green','blue']
        required_param_groups['second_fixation']=['show','units','position','radius','tolerance','num_vertices','red',
                                                  'green','blue','alpha']
        CueState.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

    def get_xml(self):
        xml_str='<state name="%s" type="effector_dissociation_cue">\n' % self.name
        xml_str+=self.get_inner_xml()
        xml_str+='</state>\n'
        return xml_str

    def init_stimulus(self):
        CueState.init_stimulus(self)

        self.f2_aspect,self.second_fixation_stim=self.init_target_stimulus('second_fixation')

    def initialize(self, run_info):
        CueState.initialize(self, run_info)
        self.target_acquired=-1
        self.blink_started=-1

    def run(self, t, visual_info, run_info, logger):

        if self.param_groups['second_fixation'].params['show'].value:
            self.second_fixation_stim.draw()

        next_state=FixationTargetState.run(self, t, visual_info, run_info, logger)

        visual_info.stimuli['%s-second_fixation' % self.name]=self.update_target_stim_info('second_fixation')

        if self.blink_started>=0:
            if t>self.blink_started+self.params['saccade_tolerance'].value:
                self.window.setColor((-1,-1,-1))
                run_info.last_state=self.name
                return self.params['fail_next_state'].value
            elif t>self.blink_started+self.params['blink_tolerance'].value:
                self.target_acquired=-1
        elif self.target_acquired>=0 and t>self.target_acquired+self.params['duration'].value:
            return self.params['success_next_state'].value

        first_fixation_pos=(self.param_groups['fixation'].params['position'].x_value,
                            self.param_groups['fixation'].params['position'].y_value)
        second_fixation_pos=(self.param_groups['second_fixation'].params['position'].x_value,
                             self.param_groups['second_fixation'].params['position'].y_value)
        if self.effector_within_tolerance_multiple(first_fixation_pos, second_fixation_pos,
            self.param_groups['fixation'].params['tolerance'].value,
            self.param_groups['second_fixation'].params['tolerance'].value,
            self.param_groups['fixation'].params['units'].value,
            self.param_groups['second_fixation'].params['units'].value):
            self.window.setColor((-1,-1,-1))
            if self.target_acquired<0:
                self.target_acquired=t
            self.blink_started=-1
        else:
            self.window.setColor(convert_color_to_psychopy((self.param_groups['effector_error_color'].params['red'].value,
                                                            self.param_groups['effector_error_color'].params['green'].value,
                                                            self.param_groups['effector_error_color'].params['blue'].value)))
            if self.blink_started<0:
                self.blink_started=t

        if self.abort_motion(self.params['check_motion'].value, self.params['check_lick'].value):
            return self.params['fail_next_state'].value
            #if self.blink_started<0:
            #    self.blink_started=t

        return next_state


class MemoryState(SingleTargetState):

    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.extend(['variability','blink_tolerance','saccade_tolerance','check_motion','check_lick'])
        required_param_groups['effector_error_color']=['red','green','blue']
        required_param_groups['motion_error_color']=['red','green','blue']
        required_param_groups['lick_error_color']=['red','green','blue']
        SingleTargetState.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

    def get_xml(self):
        xml_str='<state name="%s" type="memory">\n' % self.name
        xml_str+=self.get_inner_xml()
        xml_str+='</state>\n'
        return xml_str

    def initialize(self, run_info):
        SingleTargetState.initialize(self, run_info)
        self.target_acquired=-1
        self.blink_started=-1
        self.set_actual_duration(int(self.params['duration'].value+random.random()*self.params['variability'].value))

    def run(self, t, visual_info, run_info, logger):
        next_state=SingleTargetState.run(self, t, visual_info, run_info, logger)

        if self.blink_started>=0:
            if t>self.blink_started+self.params['saccade_tolerance'].value:
                self.window.setColor((-1,-1,-1))
                run_info.last_state=self.name
                return self.params['fail_next_state'].value
            elif t>self.blink_started+self.params['blink_tolerance'].value:
                self.target_acquired=-1
        elif self.target_acquired>=0 and t>self.target_acquired+self.actual_duration:
            return self.params['success_next_state'].value

        if self.effector_within_tolerance((self.param_groups['target'].params['position'].x_value,
                                           self.param_groups['target'].params['position'].y_value),
            self.param_groups['target'].params['tolerance'].value,
            self.param_groups['target'].params['units'].value):
            self.window.setColor((-1,-1,-1))
            if self.target_acquired<0:
                self.target_acquired=t
            self.blink_started=-1
        else:
            self.window.setColor(convert_color_to_psychopy((self.param_groups['effector_error_color'].params['red'].value,
                                                            self.param_groups['effector_error_color'].params['green'].value,
                                                            self.param_groups['effector_error_color'].params['blue'].value)))
            if self.blink_started<0:
                self.blink_started=t

        if self.abort_motion(self.params['check_motion'].value, self.params['check_lick'].value):
            return self.params['fail_next_state'].value
            #if self.blink_started<0:
            #    self.blink_started=t

        return next_state

    def set_actual_duration(self, d, update_tab=True):
        self.actual_duration=d
        if update_tab:
            self.tab.actual_duration.setText(str(self.actual_duration))
            self.tab.actual_duration.resize(self.tab.actual_duration.sizeHint())


class EffectorDissociationMemoryState(FixationTargetState):
    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.extend(['variability','blink_tolerance','saccade_tolerance','check_motion','check_lick'])
        required_param_groups['effector_error_color']=['red','green','blue']
        required_param_groups['motion_error_color']=['red','green','blue']
        required_param_groups['lick_error_color']=['red','green','blue']
        FixationTargetState.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

    def get_xml(self):
        xml_str='<state name="%s" type="effector_dissociation_memory">\n' % self.name
        xml_str+=self.get_inner_xml()
        xml_str+='</state>\n'
        return xml_str

    def initialize(self, run_info):
        FixationTargetState.initialize(self, run_info)
        self.target_acquired=-1
        self.blink_started=-1
        self.set_actual_duration(int(self.params['duration'].value+random.random()*self.params['variability'].value))

    def run(self, t, visual_info, run_info, logger):
        next_state=FixationTargetState.run(self, t, visual_info, run_info, logger)

        if self.blink_started>=0:
            if t>self.blink_started+self.params['saccade_tolerance'].value:
                self.window.setColor((-1,-1,-1))
                run_info.last_state=self.name
                return self.params['fail_next_state'].value
            elif t>self.blink_started+self.params['blink_tolerance'].value:
                self.target_acquired=-1
        elif self.target_acquired>=0 and t>self.target_acquired+self.actual_duration:
            return self.params['success_next_state'].value

        # Holding
        fixation_pos=(self.param_groups['fixation'].params['position'].x_value,
                      self.param_groups['fixation'].params['position'].y_value)
        target_pos=(self.param_groups['target'].params['position'].x_value,
                    self.param_groups['target'].params['position'].y_value)
        if self.effector_within_tolerance_multiple(fixation_pos, target_pos,
            self.param_groups['fixation'].params['tolerance'].value,
            self.param_groups['target'].params['tolerance'].value,
            self.param_groups['fixation'].params['units'].value,
            self.param_groups['target'].params['units'].value):
            self.window.setColor((-1,-1,-1))
            if self.target_acquired<0:
                self.target_acquired=t
            self.blink_started=-1
        else:
            self.window.setColor(convert_color_to_psychopy((self.param_groups['effector_error_color'].params['red'].value,
                                                            self.param_groups['effector_error_color'].params['green'].value,
                                                            self.param_groups['effector_error_color'].params['blue'].value)))
            if self.blink_started<0:
                self.blink_started=t

        if self.abort_motion(self.params['check_motion'].value, self.params['check_lick'].value):
            return self.params['fail_next_state'].value
            #if self.blink_started<0:
            #    self.blink_started=t

        return next_state

    def set_actual_duration(self, d, update_tab=True):
        self.actual_duration=d
        if update_tab:
            self.tab.actual_duration.setText(str(self.actual_duration))
            self.tab.actual_duration.resize(self.tab.actual_duration.sizeHint())


class TestJoystickState(State):
    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.extend(['distance', 'success_next_state'])
        State.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

    def get_xml(self):
        xml_str='<state name="%s" type="test_joystick">\n' % self.name
        xml_str+=self.get_inner_xml()
        xml_str+='</state>\n'
        return xml_str

    def initialize(self, run_info):
        State.initialize(self, run_info)
        self.last_pos=None

    def run(self, t, visual_info, run_info, logger):
        next_state=State.run(self, t, visual_info, run_info, logger)

        if self.last_pos is not None:
            hand_dist=self.get_effector_dist('hand',self.last_pos,'norm')
            if hand_dist>=self.params['distance'].value:
                next_state=self.params['success_next_state'].value
        self.last_pos=self.hand_pos

        return next_state


class RewardState(State):

    def __init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node, required_params=[],
                 required_param_groups={}):
        required_params.extend(['duration','success_next_state','trial_interval','balance_choice'])
        required_param_groups['reward_color']=['red','green','blue']
        State.__init__(self, order, win, name, in_manager, out_manager, effector_settings, state_node,
            required_params=required_params, required_param_groups=required_param_groups)

        #self.last_rewarded_trial=0
        #self.last_success_trial=0

    def initialize(self, run_info):
        State.initialize(self, run_info)
        base_duration=self.params['duration'].value
        self.set_actual_duration(base_duration)
        if run_info.dual_trial and self.params['balance_choice'].value and not run_info.current_choice is None:
            left_choices=np.max([0,run_info.rel_choices['left']-1])
            right_choices=np.max([0,run_info.rel_choices['right']-1])
            #a=float(left_choices+0.001)/float(right_choices+0.001)
            a=float(left_choices+1)/float(right_choices+1)
            if a<=0.3:
                if run_info.current_choice=='left':
                    a_prime=np.min([3.0,(1.0/a)])
                    self.set_actual_duration(base_duration*a_prime)
                elif run_info.current_choice=='right':
                    self.set_actual_duration(base_duration*(a*0.0))
            if 0.3<a<1.0:
                if run_info.current_choice=='left':
                    a_prime=np.min([3.0,(1.0/a)])
                    self.set_actual_duration(base_duration*a_prime)
                elif run_info.current_choice=='right':
                    self.set_actual_duration(base_duration*a)
            elif 1.0<=a<3.0:
                if run_info.current_choice=='right':
                    a_prime=np.min([3.0,a])
                    self.set_actual_duration(base_duration*a_prime)
                elif run_info.current_choice=='left':
                    self.set_actual_duration(base_duration*(1.0/a))
            elif a>3.0:
                if run_info.current_choice=='right':
                    a_prime=np.min([3.0,a])
                    self.set_actual_duration(base_duration*a_prime)
                elif run_info.current_choice=='left':
                    self.set_actual_duration(base_duration*(a*0.0))


    def get_xml(self):
        xml_str='<state name="%s" type="reward">\n' % self.name
        xml_str+=self.get_inner_xml()
        xml_str+='</state>\n'
        return xml_str


    def run(self, t, visual_info, run_info, logger):
        next_state=State.run(self, t, visual_info, run_info, logger)

        if self.state_started==t:

            run_info.increment_success()

            if run_info.consecutive_successes>=self.params['trial_interval'].value and self.actual_duration>.01:
                self.window.setColor(convert_color_to_psychopy((self.param_groups['reward_color'].params['red'].value,
                                                                self.param_groups['reward_color'].params['green'].value,
                                                                self.param_groups['reward_color'].params['blue'].value)))
                self.out_manager.turn_on('reward')
                run_info.increment_rewarded()

            self.tab.trials_until_reward.setText(str(max(0,self.params['trial_interval'].value-run_info.consecutive_successes)))
            self.tab.trials_until_reward.resize(self.tab.trials_until_reward.sizeHint())

        elif t>self.state_started+self.actual_duration:
            if self.actual_duration>0.01:
                self.out_manager.turn_off('reward')
            self.window.setColor((-1,-1,-1))
            return self.params['success_next_state'].value

        return next_state

    def set_actual_duration(self, d, update_tab=True):
        self.actual_duration=d
        if update_tab:
            self.tab.actual_duration.setText(str(self.actual_duration))
            self.tab.actual_duration.resize(self.tab.actual_duration.sizeHint())
