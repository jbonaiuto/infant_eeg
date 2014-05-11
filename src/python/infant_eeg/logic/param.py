from PySide import QtGui, QtCore
import os

class ParamContainingObject(QtCore.QObject):

    def __init__(self, name, node, required_params=[], required_param_groups={}):
        QtCore.QObject.__init__(self)
        self.name=name
        self.params={}
        self.param_groups={}
        self.read_params(node)
        self.validate_params(required_params, required_param_groups)

    def read_params(self, state_node):
        params_node=state_node.find('parameters')
        param_node_list=params_node.findall('parameter')
        for idx,param_node in enumerate(param_node_list):
            param_type=param_node.attrib['type']
            param=None
            if param_type=='boolean':
                param=BooleanParam(idx, param_node)
            elif param_type=='number':
                param=NumberParam(idx, param_node)
            elif param_type=='string':
                param=StringParam(idx, param_node)
            elif param_type=='position':
                param=PositionParam(idx, param_node)
            elif param_type=='choice':
                param=ChoiceParam(idx, param_node)
            elif param_type=='dynamic_choice':
                param=DynamicChoiceParam(idx, param_node)
            elif param_type=='dynamic_multichoice':
                param=DynamicMultiChoiceParam(idx, param_node)
            elif param_type=='file':
                param=FileParam(idx, param_node)
            if param is not None:
                self.params[param.name]=param
        param_group_node_list=params_node.findall('parameter_group')
        for idx, param_group_node in enumerate(param_group_node_list):
            param_group=ParameterGroup(idx, param_group_node)
            self.param_groups[param_group.name]=param_group

    def validate_params(self,required_params,required_param_groups):
        for param in required_params:
            if param not in self.params:
                print('State: %s, Missing parameter: %s' % (self.name, param))
        for group_name, group_params in required_param_groups.iteritems():
            if group_name not in self.param_groups:
                print('State: %s, Missing parameter group: %s' % (self.name, group_name))
            else:
                for param in group_params:
                    if param not in self.param_groups[group_name].params:
                        print('State: %s, Missing parameter: %s, from parameter group: %s' % (self.name, param,
                                                                                              group_name))

    def get_inner_xml(self):
        xml_str='<parameters>\n'
        sorted_params=sorted(self.params.iteritems(), key=lambda x: x[1].order)
        for param_name, param in sorted_params:
            xml_str+=param.get_xml()
        sorted_param_groups=sorted(self.param_groups.iteritems(), key=lambda x: x[1].order)
        for param_group_name, param_group in sorted_param_groups:
            xml_str+=param_group.get_xml()
        xml_str+='</parameters>\n'
        return xml_str



class Param(QtCore.QObject):
    def __init__(self, idx, param_node):
        QtCore.QObject.__init__(self)
        self.order=idx
        self.name=param_node.attrib['name']
        self.value=None
        self.update_sql=''

    def get_xml(self):
        return '<parameter name="%s" type="%%s">%s</parameter>\n' % (self.name, str(self.value))


class FileParam(Param):
    def __init__(self, idx, param_node):
        Param.__init__(self, idx, param_node)
        self.value=param_node.text
        self.dir=param_node.attrib['dir']
        self.path=os.path.join(self.dir,self.value)

    def get_xml(self):
        return '<parameter name="%s" type="file" dir="%s">%s</parameter>\n' % (self.name, self.dir, self.value)


class ChoiceParam(Param):
    def __init__(self, idx, param_node):
        Param.__init__(self, idx, param_node)
        self.value=param_node.attrib['value']
        options_node=param_node.find('options')
        self.options=[]
        option_list=options_node.findall('option')
        for option_node in option_list:
            self.options.append(option_node.text)

    def get_xml(self):
        xml_str='<parameter name="%s" type="choice" value="%s">\n' % (self.name, str(self.value))
        xml_str+='<options>\n'
        for option in self.options:
            xml_str+='<option>%s</option>\n' % option
        xml_str+='</options>\n'
        xml_str+='</parameter>\n'
        return xml_str


class DynamicChoiceParam(Param):
    def __init__(self, idx, param_node):
        Param.__init__(self, idx, param_node)
        self.value=param_node.text
        self.options_type=param_node.attrib['options_type']

    def get_xml(self):
        return '<parameter name="%s" type="dynamic_choice" options_type="%s">%s</parameter>\n' % (self.name,
                                                                                                  self.options_type,
                                                                                                  self.value)

class DynamicMultiChoiceParam(Param):
    def __init__(self, idx, param_node):
        Param.__init__(self, idx, param_node)
        self.options_type=param_node.attrib['options_type']
        self.selected_options=[]
        options_list=param_node.find('selected_options').findall('option')
        for option_node in options_list:
            self.selected_options.append(option_node.text)

    def get_xml(self):
        xml_str='<parameter name="%s" type="dynamic_multichoice" options_type="%s">\n' % (self.name, self.options_type)
        xml_str+='<selected_options>\n'
        for selected_option in self.selected_options:
            xml_str+='<option>%s</option>\n' % selected_option
        xml_str+='</selected_options>\n'
        xml_str+='</parameter>\n'
        return xml_str


class BooleanParam(Param):
    def __init__(self, idx, param_node):
        Param.__init__(self, idx, param_node)
        val_txt=param_node.text.lower()
        self.value=(val_txt=='true' or val_txt=='t' or val_txt=='1')

    def get_xml(self):
        return Param.get_xml(self) % 'boolean'


class NumberParam(Param):
    def __init__(self, idx, param_node):
        Param.__init__(self, idx, param_node)
        self.value=float(param_node.text)
        self.min=float(param_node.attrib['min'])
        self.max=float(param_node.attrib['max'])
        self.decimals=float(param_node.attrib['decimals'])
        self.single_step=float(param_node.attrib['single_step'])

    def get_xml(self):
        return '<parameter name="%s" type="number" min="%s" max="%s" decimals="%s" single_step="%s">%s</parameter>\n' %\
               (self.name, str(self.min), str(self.max), str(self.decimals), str(self.single_step), str(self.value))


class PositionParam(Param):
    def __init__(self, idx, param_node):
        Param.__init__(self, idx, param_node)

        x_node=param_node.find('x')
        self.x_value=float(x_node.text)
        self.x_min=float(x_node.attrib['min'])
        self.x_max=float(x_node.attrib['max'])
        self.x_decimals=float(x_node.attrib['decimals'])
        self.x_single_step=float(x_node.attrib['single_step'])

        y_node=param_node.find('y')
        self.y_value=float(y_node.text)
        self.y_min=float(y_node.attrib['min'])
        self.y_max=float(y_node.attrib['max'])
        self.y_decimals=float(y_node.attrib['decimals'])
        self.y_single_step=float(y_node.attrib['single_step'])

    def get_xml(self):
        xml_str='<parameter name="%s" type="position">\n' % self.name
        xml_str+='<x min="%s" max="%s" decimals="%s" single_step="%s">%s</x>' % (str(self.x_min), str(self.x_max),
                                                                                 str(self.x_decimals),
                                                                                 str(self.x_single_step),
                                                                                 str(self.x_value))
        xml_str+='<y min="%s" max="%s" decimals="%s" single_step="%s">%s</y>' % (str(self.y_min), str(self.y_max),
                                                                                 str(self.y_decimals),
                                                                                 str(self.y_single_step),
                                                                                 str(self.y_value))
        xml_str+='</parameter>\n'
        return xml_str


class StringParam(Param):
    def __init__(self, idx, param_node):
        Param.__init__(self, idx, param_node)
        self.value=param_node.text

    def get_xml(self):
        return Param.get_xml(self) % 'string'


class ParameterGroup():
    def __init__(self, idx, group_node):
        self.order=idx
        self.name=group_node.attrib['name']
        self.params={}
        param_node_list=group_node.findall('parameter')
        for param_idx, param_node in enumerate(param_node_list):
            param_type=param_node.attrib['type']
            param=None
            if param_type=='boolean':
                param=BooleanParam(param_idx, param_node)
            elif param_type=='number':
                param=NumberParam(param_idx, param_node)
            elif param_type=='string':
                param=StringParam(param_idx, param_node)
            elif param_type=='position':
                param=PositionParam(param_idx, param_node)
            elif param_type=='choice':
                param=ChoiceParam(param_idx, param_node)
            elif param_type=='dynamic_choice':
                param=DynamicChoiceParam(param_idx, param_node)
            elif param_type=='dynamic_multichoice':
                param=DynamicMultiChoiceParam(param_idx, param_node)
            elif param_type=='file':
                param=FileParam(param_idx, param_node)

            if param is not None:
                self.params[param.name]=param

    def get_xml(self):
        xml_str='<parameter_group name="%s">\n' % self.name
        sorted_params=sorted(self.params.iteritems(), key=lambda x: x[1].order)
        for param_name, param in sorted_params:
            xml_str+=param.get_xml()
        xml_str+='</parameter_group>\n'
        return xml_str

