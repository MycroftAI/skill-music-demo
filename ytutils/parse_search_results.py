import json

def get_info(line):
    if line.find("videoId") > 0:
        start_pos = line.find("videoId") + 10
        end_pos = line.find('"', start_pos)
        img_start = line.find('"url"',end_pos)
        img_end = line.find("?",img_start+5)
        title_tag = '"title":{"runs":[{"text":"'
        title_start = line.find(title_tag,img_end)
        title_end = line.find('"',title_start+len(title_tag)+2)
        print( line[start_pos:end_pos] )
        print( line[img_start+7:img_end] )
        print( line[title_start+len(title_tag):title_end] )
        sys.exit()


def get_json():
    fh = open("/tmp/search_results.html")
    tag = 'var ytInitialData ='
    for line in fh:

        if line.find(tag) != -1:
            la = line.split("</script>")
            ctr = 0
            for l in la:
                ctr += 1
                if l.find(tag) != -1:
                    start_indx = l.find(tag) + len(tag) + 1
                    fh.close()
                    return l[start_indx:-1]
    fh.close()
    return ''


vid_json = json.loads( get_json() )

contents = vid_json['contents']
rend = contents['twoColumnSearchResultsRenderer']
rend = rend['primaryContents']
rend = rend['sectionListRenderer']
rend = rend['contents']
rend = rend[0]
rend = rend['itemSectionRenderer']
rend = rend['contents']
rend = rend[0]
rend = rend['videoRenderer']

# at this point rend is the first video renderer
video_id = rend['videoId']
thumb = rend['thumbnail']['thumbnails'][0]
title = rend['title']['runs'][0]['text']

# sometimes we have artist and song
ta = title.split(" - ")
artist = ta[0]
song = artist
if len(ta) > 1:
    song = ta[1]

print("videoId:%s" % (video_id,))
print("thumb:%s" % (thumb,))
print("artist:%s" % (artist,))
print("song:%s" % (song,))
