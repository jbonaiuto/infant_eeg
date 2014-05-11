import copy
from psychopy import visual
from infant_eeg.logic.param import ParamContainingObject
from infant_eeg.util import convert_color_to_psychopy

class EffectorSettings(ParamContainingObject):

    def __init__(self, effector_node, myWin, required_params=[], required_param_groups={}):
        required_params.extend(['effector_control','window_constraint'])
        ParamContainingObject.__init__(self, "effector_settings", effector_node, required_params=required_params,
            required_param_groups=required_param_groups)
        self.window=myWin
        self.stim_aspects={}
        self.stim={}
        for group_name, group in self.param_groups.iteritems():
            if group_name=='eye' or group_name=='hand':
                self.stim_aspects[group_name]=1.0
                if self.window is not None:
                    if group.params['units'].value=='norm':
                        self.stim_aspects[group_name]=float(self.window.size[0])/float(self.window.size[1])
                    color=convert_color_to_psychopy((group.params['red'].value,group.params['green'].value,
                                                     group.params['blue'].value))
                    self.stim[group_name]=visual.ShapeStim(self.window, fillColor=color, lineColor=color,
                        vertices=self.get_vertex_list(group.params['radius'].value, self.stim_aspects[group_name]),
                        pos=(0,0), units=group.params['units'].value)

    def get_vertex_list(self, radius, aspect):
        return [[-radius/aspect,-radius],[ -radius/aspect,radius],[radius/aspect,radius], [radius/aspect,-radius]]

    def update_all(self, input_manager, visual_info):
        for group_name, group in self.param_groups.iteritems():
            if group_name=='eye' or group_name=='hand':
                pos=copy.copy(input_manager.read(group_name))

                if group.params['show'].value:
                    self.stim[group_name].setPos(pos)
                    self.stim[group_name].draw()

    def get_xml(self):
        xml='<effector_settings>\n'
        xml+=self.get_inner_xml()
        xml+='</effector_settings>\n'
        return xml

    def update_number_params(self):
        ParamContainingObject.update_number_params(self)

        for group_name, group in self.param_groups.iteritems():
            if group_name=='eye' or group_name=='hand':
                vertex_list=self.get_vertex_list(group.params['radius'].value, self.stim_aspects[group_name])
                self.stim[group_name].setVertices(vertex_list)

                color=convert_color_to_psychopy((group.params['red'].value,
                                                 group.params['green'].value,
                                                 group.params['blue'].value))
                self.stim[group_name].setFillColor(color,'rgb')
                self.stim[group_name].setLineColor(color,'rgb')
                self.stim[group_name].setOpacity(group.params['alpha'].value)

