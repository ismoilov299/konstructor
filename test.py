import requests
url = "https://youtube-video-fast-downloader-24-7.p.rapidapi.com/download_video/f6uDYzmzby0"
querystring = {"quality":"247"}
headers = {
    "x-rapidapi-key": "532d0e9edemsh5566c31aceb7163p1343e7jsn11577b0723dd",
    "x-rapidapi-host": "youtube-video-fast-downloader-24-7.p.rapidapi.com"
}
response = requests.get(url, headers=headers, params=querystring)
print(response.json())