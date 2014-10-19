VAGABOND_API_VERSION={{version}}

config = {
    # Typically set to the same name as the directory the project was created in
    'vmname':'{{vmname}}',

    # hostname of the machine
    'hostname':'box1',

    # You must set 1 media type.  Make sure the other options are set to None
    'media':{
        'iso':'{{iso}}',
        'vmdx':None,
        'vdi':None,
    },

    # The settings for the vm hard drie.
    'hdd':{
        'size':'32768'
    },

    # Select OS type.  To see types run vagabond list --ostypes
    'ostype':'Ubuntu_64',
}
