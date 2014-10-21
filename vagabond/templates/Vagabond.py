VAGABOND_API_VERSION={{version}}

config = {
    'vm': {
        'box':'addgene_base',
        'hostname':'jfvm1'
    }

    # Typically set to the same name as the directory the project was created in
    'vmname':'{{vmname}}',

    # hostname of the machine
    'hostname':'box1',

    # Select OS type.  To see types run vagabond list --ostypes
    'ostype':'Ubuntu_64',

    'box':{
        'local':None,
        'url':None
    }   

    # You must set 1 media type.  Make sure the other options are set to None
    'media':{
        'box':{% if box %}'{{box}}'{% else %}None{% endif %},
        'iso':{% if iso %}'{{iso}}'{% else %}None{% endif %},
        'vdi':{% if vdi %}'{{vdi}}'{% else %}None{% endif %},
        'vmdx':{% if vmdx %}'{{vmdx}}'{% else %}None{% endif %},
    },

    # The settings for the vm hard drie.
    'hdd':{
        'size':'32768'
    },

}
