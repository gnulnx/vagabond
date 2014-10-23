VAGABOND_API_VERSION={{version}}

config = {
    'vm': {
        {%- if box %}
        # The name of the vagabond/vagrant box to use
        'box':'{{box}}',
        {% endif -%}

        {%- if iso %}
        # Import the box from a local iso image
        'iso':'{{iso}}',
        {% endif -%}

        {%- if hostname %}
        # Set the hostname of the virtual machine
        'hostname':'{{hostname}}'
        {% endif -%}
    },

    # Select OS type.  To see types run vagabond list --ostypes
    # I believe this is only relevant if you are starting from iso
    'ostype':'Ubuntu_64',


    # The settings for the vm hard drie.
    # Would this make more since in the vm section?
    'hdd':{
        'size':'32768'
    },

}
