import pickle

pickle.dump(
    {
        'spotify_email': 'SPOTIFY_EMAIL',
        'spotify_pass': 'SPOTIFY_PASSWORD',
        'youtube_email': 'YOUTUBE EMAIL',
        'youtube_pass': 'YOUTUBE_PASSWORD'
    },
    open('user_info.dat', 'wb')
)