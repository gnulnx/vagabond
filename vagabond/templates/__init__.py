import os
from jinja2 import Template as Template
#from django.template import Template
from django.template import Context
from django.conf import settings

settings.configure()

class BaseTemplate:

    """ 
        This is the base class for template rendering
        Each template to render should extend from this class and 
        override minimalliy the context and template properties.
    """

    # absolute path to the template file
    template = ''   

    # The context that will be passed to the template
    # Sublcasses should specify their own context parameters
    context = {}

    @classmethod
    def render(cls, c={}):
        """
            Pass in a context our the defaults above will be used
        """
        cls.context.update(c)
        t = Template( open(cls.template).read() )
        c = Context( cls.context )
        return t.render( **cls.context )

    @classmethod
    def save(cls, path, **kwargs):
        """
            path is the path to where the file will be saved
        """
        c = kwargs.get('context', cls.context)
        with open(path, 'w') as f:
            f.write(cls.render(c) )

class VagabondTemplate(BaseTemplate):
    template = os.path.dirname(os.path.realpath(__file__)) + "/Vagabond.py"
    context = {
        'NAME':'site1',
        'PRIVATE':'192.168.100.100', #To use private network set to ip:  192.168.100.100
    } 
