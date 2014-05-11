import math
import random
from infant_eeg.logic.param import ParamContainingObject

class TargetGenerator(ParamContainingObject):

    def __init__(self, generator_node, required_params=[], required_param_groups={}):
        ParamContainingObject.__init__(self, 'target_generator', generator_node, required_params=required_params,
            required_param_groups=required_param_groups)
        self.targetPositions=[]
        self.currentTargetIdx=0
        self.init_targets()

    def init_targets(self):
        pass

    def iter_trial(self):
        pass

    def get_current_target(self):
        return {'target': self.targetPositions[self.currentTargetIdx]}

    def get_xml(self):
        xml='<target_generator type="%s">\n'
        xml+=self.get_inner_xml()
        xml+='</target_generator>\n'
        return xml


class StaticTargetGenerator(TargetGenerator):
    def __init__(self, generator_node, required_params=[], required_param_groups={}):
        required_params.extend(['units','random','states_to_update'])
        self.num_targets=0
        TargetGenerator.__init__(self, generator_node, required_params=required_params,
            required_param_groups=required_param_groups)

    def init_targets(self):
        TargetGenerator.init_targets(self)
        self.targetPositions=[]
        sorted_param_groups=sorted(self.param_groups.iteritems(), key=lambda x: x[1].order)
        self.num_targets=0
        for param_group_name, param_group in sorted_param_groups:
            if param_group_name.startswith('target_'):
                self.targetPositions.append([param_group.params['position'].x_value,
                                             param_group.params['position'].y_value])
                self.num_targets+=1

    def iter_trial(self):
        if not self.params['random'].value:
            # Advance target with wraparound
            self.currentTargetIdx+=1
            if self.currentTargetIdx>=self.num_targets:
                self.currentTargetIdx=0
            elif self.currentTargetIdx<0:
                self.currentTargetIdx=self.num_targets-1
        else:
            self.currentTargetIdx=random.choice(range(self.num_targets))

    def get_xml(self):
        xml='<target_generator type="static">\n'
        xml+=self.get_inner_xml()
        xml+='</target_generator>\n'
        return xml


class DualStaticTargetGenerator(StaticTargetGenerator):
    def __init__(self, generator_node, required_params=[], required_param_groups={}):
        required_params.extend(['flip_horizontal','flip_vertical','flip_percentage'])
        StaticTargetGenerator.__init__(self, generator_node, required_params=required_params,
            required_param_groups=required_param_groups)

    def get_current_target(self):
        t=self.targetPositions[self.currentTargetIdx]
        t_prime=(t[0],t[1])

        if random.random()<self.params['flip_percentage'].value:
            if self.params['flip_horizontal'].value and not self.params['flip_vertical'].value:
                t_prime=(-1*t[0],t[1])
            elif self.params['flip_vertical'].value and not self.params['flip_horizontal'].value:
                t_prime=(t[0],-1*t[1])
            elif self.params['flip_horizontal'].value and self.params['flip_vertical'].value:
                t_prime=(-1*t[0],-1*t[1])
        return {'target': t, 'target_prime': t_prime}

    def get_xml(self):
        xml='<target_generator type="dual_static">\n'
        xml+=self.get_inner_xml()
        xml+='</target_generator>\n'
        return xml


class DynamicTargetGenerator(TargetGenerator):
    def __init__(self, generator_node, required_params=[], required_param_groups={}):
        required_params.extend(['units','num_targets','direction','position_radius','states_to_update',
                                'radius_variability','angle_variability'])
        TargetGenerator.__init__(self, generator_node, required_params=required_params,
            required_param_groups=required_param_groups)

    def get_current_target(self):
        angle_var=self.params['angle_variability'].value*(math.pi/180.0)
        targetPosAngle=2*math.pi/float(self.params['num_targets'].value)*(self.currentTargetIdx+1)+\
                       random.uniform(-angle_var,angle_var)
        rad=self.params['position_radius'].value+random.uniform(-self.params['radius_variability'].value,
            self.params['radius_variability'].value)
        return {'target':[rad*math.sin(targetPosAngle),rad*math.cos(targetPosAngle)]}

    def iter_trial(self):
        # Advance target with wraparound
        iter=0
        if self.params['direction'].value=='clockwise':
            iter=1
        elif self.params['direction'].value=='counter-clockwise':
            iter=-1
        self.currentTargetIdx+=iter
        if self.currentTargetIdx>=self.params['num_targets'].value:
            self.currentTargetIdx=0
        elif self.currentTargetIdx<0:
            self.currentTargetIdx=self.params['num_targets'].value-1

    def get_xml(self):
        xml='<target_generator type="dynamic">\n'
        xml+=self.get_inner_xml()
        xml+='</target_generator>\n'
        return xml
