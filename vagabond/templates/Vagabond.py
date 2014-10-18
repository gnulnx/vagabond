VAGABOND_API_VERSION={{version}}

config = {
    'hostname':'box1',

    # You must set 1 media type.  Make sure the other options are set to None
    'media':{
        'iso':'/Users/jfurr/Downloads/ubuntu-14.04.1-desktop-amd64.iso',
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
