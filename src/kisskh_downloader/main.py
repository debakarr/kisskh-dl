from kisskh_downloader.downloader import Mu38Extracter, Mu3u8Selector
from kisskh_downloader.kisskh_api import KissKHApi
from operator import itemgetter

if __name__ == "__main__":
    k = KissKHApi()
    me = Mu38Extracter()
    
    dramas = k.get_dramas("Ghost Doctor")
    start = 7
    stop = 16
    quality = "720"
    episode_range = range(start, stop + 1)
    for drama_id, drama_name in dramas.items():
        episode_urls = k.get_episode_urls(drama_id)
        episode_keys = list(episode_urls.keys())
        if start <episode_keys[0] or stop > episode_keys[-1]:
            raise ValueError("Invalid episode start or stop count")
        
        for episode in episode_range:
            urls = me.extract(episode_urls.get(episode))
            
            for url in urls:
                ms = Mu3u8Selector(url)
                videos = ms.get_videos()
                outfile = f"{drama_name}/{drama_name}_{quality}_E{episode:02d}.ts"
                ms.download_playlist_segments(outfile, videos.get(quality))