VAGABOND_API_VERSION={{version}}

config = {
    'vm': {
        {% if box -%}
        # The name of the vagabond/vagrant box to use
        'box':'{{box}}',
        {% endif -%}

        {%- if iso -%}
        # Import the box from a local iso image
        'iso':'{{iso}}',
        {%- endif -%}

        'hostname':{% if hostname %}'{{hostname}}'{% else %}'vagabond_vm'{%endif%},
    },

    # Typically set to the same name as the directory the project was created in
    'vmname':'{{vmname}}',

    # hostname of the machine
    'hostname':'box1',

    # Select OS type.  To see types run vagabond list --ostypes
    'ostype':'Ubuntu_64',


    # The settings for the vm hard drie.
    # Would this make more since in the vm section?
    'hdd':{
        'size':'32768'
    },

}
