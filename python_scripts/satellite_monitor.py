import aiohttp
import asyncio
import time
import json
import os

NO_PASSES = '{"info":{"satid":25544,"satname":"SPACE STATION","transactionscount":2,"passescount":0}}'
SIX_PASSES = '{"info":{"satid":25544,"satname":"SPACE STATION","transactionscount":0,"passescount":6},"passes":[{"startAz":329.8,"startAzCompass":"NW","startEl":0.17,"startUTC":1580689995,"maxAz":23.14,"maxAzCompass":"NNE","maxEl":10.05,"maxUTC":1580690255,"endAz":76.24,"endAzCompass":"E","endEl":9.53,"endUTC":1580690510,"mag":0.4,"duration":215},{"startAz":320.21,"startAzCompass":"NW","startEl":0.13,"startUTC":1580779325,"maxAz":35,"maxAzCompass":"NE","maxEl":32.49,"maxUTC":1580779640,"endAz":112.7,"endAzCompass":"ESE","endEl":10.81,"endUTC":1580779950,"mag":0.4,"duration":140},{"startAz":324.2,"startAzCompass":"NW","startEl":0.26,"startUTC":1580862880,"maxAz":31.98,"maxAzCompass":"NE","maxEl":20.72,"maxUTC":1580863180,"endAz":100.31,"endAzCompass":"E","endEl":20.22,"endUTC":1580863475,"mag":-0.4,"duration":275},{"startAz":327.09,"startAzCompass":"NW","startEl":0.07,"startUTC":1580946430,"maxAz":27.84,"maxAzCompass":"NNE","maxEl":14.19,"maxUTC":1580946715,"endAz":88.49,"endAzCompass":"E","endEl":9.1,"endUTC":1580946995,"mag":0,"duration":415},{"startAz":310.54,"startAzCompass":"NW","startEl":0.27,"startUTC":1580952220,"maxAz":220.45,"maxAzCompass":"SW","maxEl":72.85,"maxUTC":1580952545,"endAz":138.07,"endAzCompass":"SE","endEl":22.54,"endUTC":1580952860,"mag":-0.5,"duration":205},{"startAz":315.77,"startAzCompass":"NW","startEl":0.18,"startUTC":1581035765,"maxAz":40.83,"maxAzCompass":"NE","maxEl":58.06,"maxUTC":1581036090,"endAz":125.22,"endAzCompass":"SE","endEl":44.18,"endUTC":1581036405,"mag":-2,"duration":370}]}'
TOO_FAINT = '{"info":{"satid":33591,"satname":"NOAA 19","transactionscount":9,"passescount":1},"passes":[{"startAz":18.8,"startAzCompass":"NNE","startEl":0.07,"startUTC":1580555655,"maxAz":101.38,"maxAzCompass":"E","maxEl":54.18,"maxUTC":1580556120,"endAz":182.89,"endAzCompass":"S","endEl":0,"endUTC":1580556575,"mag":6,"duration":920}]}'

SAT_ISS = 25544
SAT_SL_G_4 = 70002
SAT_YINHE_1 = 45024
SAT_SL_4_RB = 42800
SAT_SES_1 = 36516
SAT_NOAA_19 = 33591
SAT_SHENZHOU_11 = 41868

watch_list = {"ISS": 25544, "Shenzhou 11": 41868, "SL-4 R/B": 42800, "Atlas Centaur 2 R/B": 694}

class SatData:
    def __init__(self, api_key, lat: float = None, lon: float = None, elevation: float = None):
        self.API_URL = "https://www.n2yo.com/rest/v1/satellite/"
        self.DEBUG = False
        self.api_key = api_key
        self.lat = lat
        self.lon = lon
        self.elevation = elevation

    async def get_visual_passes(self, sat_id: int, days: int, min_visible_secs: int):
        query_url = f"{self.API_URL}/visualpasses/{sat_id}/{self.lat}/{self.lon}/{self.elevation}/{days}/{min_visible_secs}/&apiKey={self.api_key}"
        async with aiohttp.ClientSession() as session:
            raw_data = await self._fetch(session, query_url)
            # if not self.DEBUG:
            #     print(f"{raw_data}")
            pass_data = json.loads(raw_data)
            # self._print_report(pass_data)
            return pass_data

    def _print_report(self, data):
        for k, v in data["info"].items():
            print(f"{k}: {v}")
            # print(f"{item}")
        print("######")
        for pass_event in data["passes"]:
            print("------")
            for k, v in pass_event.items():
                print(f"{k}: {v}")

    async def _fetch(self, session, url):
        if self.DEBUG:
            print("TEST DATA")
            test_data = SIX_PASSES
            return test_data
        async with session.get(url, ssl=False) as response:
            return await response.text()


def get_date(ts):
    local_ts = time.localtime(ts)
    if os.name == "nt":
        format_string = "%A, %B %#e at %#I:%M %p"
    else:
        format_string = "%A, %B %-d at %-I:%M %p"
    return time.strftime(format_string, local_ts)


def get_direction(abv_dir):
    if abv_dir == "N":
        direction = "north"
    elif abv_dir == "NNE":
        direction = "north-north-east"
    elif abv_dir == "NE":
        direction = "north-east"
    elif abv_dir == "ENE":
        direction = "east-north-east"
    elif abv_dir == "E":
        direction = "east"
    elif abv_dir == "ESE":
        direction = "east-south-east"
    elif abv_dir == "SE":
        direction = "south-east"
    elif abv_dir == "SSE":
        direction = "south-south-east"
    elif abv_dir == "S":
        direction = "south"
    elif abv_dir == "SSW":
        direction = "south-south-west"
    elif abv_dir == "SW":
        direction = "south-west"
    elif abv_dir == "WSW":
        direction = "west-south-west"
    elif abv_dir == "W":
        direction = "west"
    elif abv_dir == "WNW":
        direction = "west-north-west"
    elif abv_dir == "NW":
        direction = "north-west"
    elif abv_dir == "NNW":
        direction = "north-north-west"
    else:
        direction = "unknown"

    return direction


def next_pass_msg(pass_data, mag_limit: int = None):

    sat_name = pass_data["info"]["satname"].title()

    if pass_data["info"]["passescount"] == 0:
        return f"{sat_name} will not be passing over soon."

    for next_pass in pass_data["passes"]:
        if next_pass["mag"] >= mag_limit:
            response = f"The next pass of {sat_name} will be too faint."

        else:
            start_time = get_date(next_pass["startUTC"])
            start_dir = get_direction(next_pass["startAzCompass"])
            end_dir = get_direction(next_pass["endAzCompass"])
            duration = next_pass["duration"]
            mag = next_pass["mag"]

            response = f"The {sat_name} will be passing over on {start_time}.  It will be appearing in the {start_dir} and travel toward the {end_dir} being visible for {duration} seconds with a manitude of {mag}."
            break

    return response


async def main():
    key = None
    lat = None
    lon = None
    elevation = None

    days = 1
    min_visible_seconds = 5
    min_magnitude = 5

    sat_tracker = SatData(key, lat, lon, elevation)
    for sat_name, sat_id in watch_list.items():
        pass_data = await sat_tracker.get_visual_passes(sat_id, days, min_visible_seconds)
        msg = next_pass_msg(pass_data, min_magnitude)
        print(f"{msg}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

    # shut down
    loop.run_until_complete(asyncio.sleep(0.500))
    loop.close()
