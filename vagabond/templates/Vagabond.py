VAGABOND_API_VERSION={{version}}

config = {
    'vm': {
        # The name of the vagabond/vagrant box to use
        'box':{% if box %}'{{box}}'{% else %}None{% endif %},

        # Import the box from a local iso image
        'iso':{% if iso %}'{{iso}}'{% else %}None{% endif %},

        'hostname':{% if hostname %}'{{hostname}}'{% else %}'vagabond_vm'{%endif%},
    },

    # Typically set to the same name as the directory the project was created in
    'vmname':'{{vmname}}',

    # hostname of the machine
    'hostname':'box1',

    # Select OS type.  To see types run vagabond list --ostypes
    'ostype':'Ubuntu_64',


    # The settings for the vm hard drie.
    'hdd':{
        'size':'32768'
    },

}
