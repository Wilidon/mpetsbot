import asyncio
import random
import time
import traceback
from datetime import datetime

from loguru import logger
from python_rucaptcha import ImageCaptcha

from config import get_settings, get_db
from mpets import MpetsApi
from sql import crud
from utils import functions
from utils.constants import gifts_name, holiday_1402, holiday_2302, holiday_1402_prizes, holiday_2302_prizes, \
    holiday_308, holiday_308_prizes, holiday_401, holiday_401_prizes, holiday_501, holiday_501_prizes
from utils.currency import get_currency_core
from utils.functions import get_mpets_api, notice


async def check_task(user, user_task, progress, task_name):
    if user_task.end <= progress:
        crud.update_club_task(id=user_task.id,
                              progress=user_task.end,
                              status="completed")
        await functions.add_club_points(user_id=user.user_id,
                                        club_id=user.club_id,
                                        task_name=task_name)
    else:
        crud.update_club_task(user_task.id, progress)


async def checking_coin_task(mpets, user, user_task):
    pet = await mpets.view_profile(user.pet_id)
    if not pet["status"]:
        # logging
        return 0
    if pet["club_coin"] is None:
        # logging
        return 0
    progress = int(pet["club_coin"])
    await check_task(user, user_task, progress, user_task.task_name)


async def checking_heart_task(mpets, user, user_task):
    page, progress, step, counter = 1, 0, True, 0
    while step:
        try:
            pets = await mpets.club_budget_history_all(
                user.club_id, 2, page)
            if not pets["players"]:
                break
            for pet in pets["players"]:
                if pet["pet_id"] == user.pet_id:
                    progress = int(pet["count"])
                    step = False
                    break
            page += 1
        except Exception:
            counter += 1
            if counter >= 5:
                return 0
    await check_task(user, user_task, progress, user_task.task_name)


async def checking_exp_task(mpets, user, user_task):
    page, progress, step, counter = 1, 0, True, 0
    while step:
        try:
            pets = await mpets.club_budget_history_all(
                user.club_id, 3, page)
            if not pets["players"]:
                break
            for pet in pets["players"]:
                if pet["pet_id"] == user.pet_id:
                    progress = int(pet["count"])
                    step = False
                    break
            page += 1
        except Exception:
            counter += 1
            if counter >= 5:
                return 0
    await check_task(user, user_task, progress, user_task.task_name)


async def checking_getGift_task(mpets, user, user_task):
    gift_id = user_task.task_name.split("_")[-1]
    pet_gift = False
    if gift_id.isdigit() is False:
        return 0
    gifts = await mpets.view_gifts(user.pet_id)
    if int(gift_id) == 0:
        for gift in gifts["players"]:
            if "сегодня" in gift["date"]:
                pet_gift = True
        if pet_gift:
            await check_task(user, user_task, user_task.end, user_task.task_name)
    else:
        gift_id = int(gifts_name[int(gift_id) - 1][0])
        for gift in gifts["players"]:
            if gift_id in [26, 27, 35]:
                if gift["pet_id"]:
                    try:
                        if "сегодня" in gift["date"] and \
                                (int(gift["present_id"]) == 36 or
                                 int(gift["present_id"]) == 26):
                            pet_gift = True
                        elif "сегодня" in gift["date"] and \
                                (int(gift["present_id"]) == 37 or
                                 int(gift["present_id"]) == 27):
                            pet_gift = True
                        elif "сегодня" in gift["date"] and \
                                (int(gift["present_id"]) == 35 or
                                 int(gift["present_id"]) == 38):
                            pet_gift = True
                    except Exception:
                        pass
            else:
                if gift["pet_id"]:
                    try:
                        if "сегодня" in gift["date"] and \
                                int(gift["present_id"]) == int(gift_id):
                            pet_gift = True
                    except Exception:
                        pass
        if pet_gift:
            await check_task(user, user_task, user_task.end, user_task.task_name)


async def checking_sendGift_task(mpets, user, user_task, pet_id):
    gift_id = user_task.task_name.split("_")[-1]
    pet_gift = False
    if gift_id.isdigit() is False:
        return 0
    gifts = await mpets.view_gifts(pet_id)
    if int(gift_id) == 0:
        for gift in gifts["players"]:
            if gift["pet_id"]:
                try:
                    if user.pet_id == int(gift["pet_id"]) and \
                            "сегодня" in gift["date"]:
                        pet_gift = True
                except Exception:
                    pass
        if pet_gift:
            await check_task(user, user_task, user_task.end, user_task.task_name)
            return True
    else:
        gift_id = int(gifts_name[int(gift_id) - 1][0])
        for gift in gifts["players"]:
            if gift_id in [26, 27, 35]:
                if gift["pet_id"]:
                    try:
                        if "сегодня" in gift["date"] and \
                                (int(gift["present_id"]) == 36 or
                                 int(gift["present_id"]) == 26) and \
                                user.pet_id == int(gift["pet_id"]):
                            pet_gift = True
                        elif "сегодня" in gift["date"] and \
                                (int(gift["present_id"]) == 37 or
                                 int(gift["present_id"]) == 27) and \
                                user.pet_id == int(gift["pet_id"]):
                            pet_gift = True
                        elif "сегодня" in gift["date"] and \
                                (int(gift["present_id"]) == 35 or
                                 int(gift["present_id"]) == 38) and \
                                user.pet_id == int(gift["pet_id"]):
                            pet_gift = True
                    except Exception:
                        pass
            else:
                if gift["pet_id"]:
                    try:
                        if "сегодня" in gift["date"] and \
                                int(gift["present_id"]) == gift_id and \
                                user.pet_id == int(gift["pet_id"]):
                            pet_gift = True
                    except Exception:
                        pass
        if pet_gift:
            await check_task(user, user_task, user_task.end, user_task.task_name)
            return True


async def checking_chat_task(mpets, user, user_task):
    today = int(datetime.today().strftime("%Y%m%d"))
    chat = await mpets.chat(user.club_id)
    for msg in chat["messages"]:
        if crud.get_chat_message(user.club_id, user.pet_id, msg["message"],
                                 today):
            crud.update_club_task(user_task.id, user_task.end,
                                  "completed")
            await functions.add_club_points(user.user_id, user.club_id)
        else:
            if crud.get_chat_message(user.club_id, msg["pet_id"],
                                     msg["message"], today) is None:
                crud.create_chat_message(user.club_id, msg["pet_id"],
                                         msg["message"], today)


async def checking_thread_task(mpets, user, user_task):
    forums = await mpets.forums(user.club_id)
    if forums["status"] == "error":
        # logging
        return False
    progress = user_task.progress
    for i in range(0, 2):
        threads = await mpets.threads(forums["forums_id"][i]["forum_id"])
        if threads["status"] != "ok":
            continue
        for thread in threads["threads"]:
            page = 1
            thread_data = crud.get_thread_messages(thread)
            if not thread_data:
                while True:
                    thread_info = await mpets.thread(thread, page)
                    if thread_info["status"] == "error":
                        break
                    for thread_msg in thread_info["messages"]:
                        crud.create_thread_message(user.club_id,
                                                   thread_msg["pet_id"],
                                                   thread,
                                                   thread_msg["message"],
                                                   page,
                                                   thread_msg["post_date"])
                        if user.pet_id == int(thread_msg["pet_id"]):
                            progress += 1
                    page += 1
            else:
                page = crud.get_last_page_thread(thread).page
                page = int(page)
                while True:
                    thread_info = await mpets.thread(thread, page)
                    if thread_info["status"] == "error":
                        break
                    for thread_msg in thread_info["messages"]:
                        if crud.check_msg(thread, thread_msg["message"],
                                          thread_msg["post_date"],
                                          page) is None:
                            crud.create_thread_message(user.club_id,
                                                       thread_msg["pet_id"],
                                                       thread,
                                                       thread_msg["message"],
                                                       page,
                                                       thread_msg["post_date"])
                            if user.pet_id == int(thread_msg["pet_id"]):
                                progress += 1
                    page += 1
    if user_task.end <= progress:
        crud.update_club_task(user_task.id, user_task.end,
                              "completed")
        await functions.add_club_points(user.user_id, user.club_id)
    else:
        crud.update_club_task(user_task.id, progress)


async def checking_upRank_task(mpets, user, user_task):
    history = await mpets.club_history(user.club_id)
    today = datetime.today().strftime("%d.%m")
    if not history["status"]:
        # logging
        return False
    progress = user_task.progress
    for his in history["history"]:
        if user.pet_id == int(his["owner_id"]) and \
                " повысил " in his["action"] and \
                today == his["date"].split(" ")[0]:
            progress += 1
    await check_task(user, user_task, progress, user_task.task_name)


async def checking_downRank_task(mpets, user, user_task):
    history = await mpets.club_history(user.club_id)
    today = datetime.today().strftime("%d.%m")
    if not history["status"]:
        # logging
        return False
    progress = user_task.progress
    for his in history["history"]:
        if user.pet_id == int(his["owner_id"]) and \
                " понизил " in his["action"] and \
                today == his["date"].split(" ")[0]:
            progress += 1
    await check_task(user, user_task, progress, user_task.task_name)


async def checking_acceptPlayer_task(mpets, user, user_task):
    history = await mpets.club_history(user.club_id)
    today = datetime.today().strftime("%d.%m")
    if not history["status"]:
        # logging
        return 0
    progress = user_task.progress
    for his in history["history"]:
        if user.pet_id == int(his["owner_id"]) and \
                "принял" in his["action"] and \
                today == his["date"].split(" ")[0]:
            progress += 1
    await check_task(user, user_task, progress, user_task.task_name)


async def start_verify_club(club, mpets):
    try:
        today = int(datetime.today().strftime("%Y%m%d"))
        profile = await mpets.profile()
        if profile["club"] is None:
            logger.info(f"{club.bot_name} исключен из клуба ({club.club_id}).")
            crud.update_club_status(club.club_id, "excluded")
        users = crud.get_users_with_club(club.club_id)
        for user in users:
            user_tasks = crud.get_club_tasks(user.user_id, today)
            profile = await mpets.view_profile(user.pet_id)
            if profile["club_id"] is None:
                continue
            if int(profile["club_id"]) != club.club_id:
                return 0
            for user_task in user_tasks:
                try:
                    if user_task.status == "completed":
                        continue
                    elif user_task.task_name == "coin":
                        await checking_coin_task(mpets, user, user_task)
                    elif user_task.task_name == "heart":
                        await checking_heart_task(mpets, user, user_task)
                    elif user_task.task_name == "exp":
                        await checking_exp_task(mpets, user, user_task)
                    elif "get_gift" in user_task.task_name or \
                            "get_random_gift" in user_task.task_name:
                        await checking_getGift_task(mpets, user, user_task)
                    elif user_task.task_name == "chat":
                        await checking_chat_task(mpets, user, user_task)
                    elif user_task.task_name == "thread":
                        pass
                        # await checking_thread_task(mpets, user, user_task)
                    elif user_task.task_name == "upRank":
                        await checking_upRank_task(mpets, user, user_task)
                    elif user_task.task_name == "downRank":
                        await checking_downRank_task(mpets, user, user_task)
                    elif user_task.task_name == "acceptPlayer":
                        await checking_acceptPlayer_task(mpets, user, user_task)
                except Exception as e:
                    log = logger.bind(context=e)
                    log.error(f"Не удалось задание у клуба({club.club_id})"
                              f"пользователь {user.user_id}"
                              f"ошибка {e}")
    except Exception as e:
        log = logger.bind(context=traceback.format_exc())
        log.error(f"Не удалось проверить клуб({club.club_id}) \n")


async def start_verify_account(club, mpets):
    profile = await mpets.profile()
    if profile and not profile["status"]:
        log = logger.bind(context=profile)
        log.warning("Не удалось получить профиль.")
        return False
    if profile["club"] is not None:
        crud.update_club_last_active(club_id=club.club_id)
        logger.success(f"Клуб ({club.club_id}) подтвержден.")
        crud.update_club_status(club.club_id, "ok")


async def checking_bots():
    logger.debug("start checking_bots")
    settings = get_settings()
    while True:
        try:
            clubs_with_status_ok = crud.get_clubs(status="ok")
            clubs_with_status_waiting = crud.get_clubs(status="waiting")
            clubs_with_status_freeze = crud.get_clubs(status="freeze")
            tasks = []
            time0 = time.time()
            for i in range(0, len(clubs_with_status_ok)):

                club = clubs_with_status_ok[i]
                mpets = await get_mpets_api(club=club, api_key=settings.api_key)
                task = asyncio.create_task(start_verify_club(club,
                                                             mpets))
                tasks.append(task)
                if len(tasks) >= 20:
                    await asyncio.gather(*tasks)
                    await asyncio.sleep(1)
                    tasks = []
                elif i + 1 == len(clubs_with_status_ok):
                    await asyncio.gather(*tasks)
                    await asyncio.sleep(1)
                    tasks = []
            for i in range(0, len(clubs_with_status_waiting)):
                club = clubs_with_status_waiting[i]
                mpets = await get_mpets_api(club=club, api_key=settings.api_key)
                if mpets is False:
                    crud.update_club_status(club_id=club.club_id,
                                            status="excluded")
                task = asyncio.create_task(start_verify_account(club, mpets))
                tasks.append(task)
                if len(tasks) >= 20:
                    await asyncio.gather(*tasks)
                    await asyncio.sleep(1)
                    tasks = []
                elif i + 1 == len(clubs_with_status_waiting):
                    await asyncio.gather(*tasks)
                    await asyncio.sleep(1)
                    tasks = []
            for i in range(0, len(clubs_with_status_freeze)):
                club = clubs_with_status_freeze[i]
                crud.update_club_last_active(club_id=club.club_id, difference=86400)
                mpets = await get_mpets_api(club=club, api_key=settings.api_key)
                if mpets is False:
                    crud.update_club_status(club_id=club.club_id,
                                            status="excluded")
                task = asyncio.create_task(start_verify_account(club, mpets))
                tasks.append(task)
                if len(tasks) >= 20:
                    await asyncio.gather(*tasks)
                    await asyncio.sleep(1)
                    tasks = []
                elif i + 1 == len(clubs_with_status_freeze):
                    await asyncio.gather(*tasks)
                    await asyncio.sleep(1)
                    tasks = []
            total_time = int(time.time() - time0)
            crud.health(clubtasks=total_time)
            await asyncio.sleep(1)
        except Exception as e:
            # raise
            logger.error(e)
            await asyncio.sleep(10)


async def update_user_data():
    logger.debug("start update_user_data")
    settings = get_settings()
    mpets = MpetsApi(name=settings.bot1,
                     password=settings.bot_password,
                     rucaptcha_api=settings.api_key)
    r = await mpets.login()
    logger.bind(context=r).success("Функция обновления данных пользователей "
                                   "запущена.")
    while True:
        try:
            time0 = time.time()
            users = crud.get_users()
            for user in users:
                if user.pet_id == 0:
                    continue
                profile = await mpets.view_profile(user.pet_id)
                if not profile['status']:
                    log = logger.bind(context=profile)
                    log.warning(f"Не удалось обновить информацию "
                                f"пользователя {user.user_id}")
                    continue
                user = crud.get_user(user.user_id)
                if user.club_id is not None:
                    if profile["club_id"] is None:
                        crud.reset_user_stats(user.user_id)
                        stats = crud.get_user_stats(user.user_id)
                        logger.warning(f"Сбросил статистику пользователя "
                                       f"{user.user_id}. У него было "
                                       f"{stats.club_tasks} ёлок и "
                                       f"{stats.club_points} фишек.")
                    elif int(user.club_id) != int(profile["club_id"]):
                        crud.reset_user_stats(user.user_id)
                        stats = crud.get_user_stats(user.user_id)
                        logger.warning(f"Сбросил статистику пользователя "
                                       f"{user.user_id}. У него было "
                                       f"{stats.club_tasks} ёлок и "
                                       f"{stats.club_points} фишек.")
                crud.update_user_data(user.user_id, profile["pet_id"],
                                      profile["name"], profile["club_id"])
            total_time = int(time.time() - time0)
            crud.health(userinfo=total_time)
            await asyncio.sleep(3600)
        except Exception as e:
            logger.error(e)
            await asyncio.sleep(3)


async def checking_avatar_task(mpets, user, user_task):
    profile = await mpets.view_profile(user.pet_id)
    if not profile["status"]:
        return 0
    task_name = user_task.task_name
    avatar_id = user_task.task_name.split("_")[-1]
    avatar_id = avatar_id.rsplit(":", maxsplit=1)[0]
    if int(functions.avatar_name[int(avatar_id)][0]) == int(profile["ava_id"]):
        ava = task_name.split("_", maxsplit=1)[-1]
        start_time = ava.rsplit(":", maxsplit=1)[1]
        if int(start_time) == 0:
            task_name = f"avatar_{avatar_id}:{int(time.time())}"
            crud.update_user_task_name(user_task.id, task_name)
        else:
            left_time = time.time() - int(start_time)
            if left_time >= 3600:
                crud.update_user_task(user_task.id, user_task.end, "completed")
                await functions.add_user_points(user_id=user.user_id,
                                                task_name="avatar")
            else:
                left_time = int(left_time // 60)
                crud.update_user_task(user_task.id, left_time, "waiting")
    else:
        task_name = f"avatar_{avatar_id}:0"
        crud.update_user_task(user_task.id, 0, "waiting")
        crud.update_user_task_name(user_task.id, task_name)


async def checking_anketa_task(mpets, user, user_task):
    profile = await mpets.view_anketa(user.pet_id)
    if not profile["status"]:
        return 0
    task_name = user_task.task_name
    anketa_about = task_name.split("_", maxsplit=1)[-1]
    anketa_about = anketa_about.rsplit(":", maxsplit=1)[0]
    if anketa_about != profile["about"]:
        ank = task_name.split("_", maxsplit=1)[-1]
        start_time = ank.rsplit(":", maxsplit=1)[1]
        if int(start_time) == 0:
            task_name = f"anketa_{anketa_about}:{int(time.time())}"
            crud.update_user_task_name(user_task.id, task_name)
        else:
            left_time = time.time() - int(start_time)
            if left_time >= 1800:
                crud.update_user_task(user_task.id, user_task.end, "completed")
                await functions.add_user_points(user_id=user.user_id,
                                                task_name="anketa")
            else:
                left_time = int(left_time // 60)
                crud.update_user_task(user_task.id, left_time, "waiting")
    else:
        task_name = f"anketa_{anketa_about}:0"
        crud.update_user_task(user_task.id, 0, "waiting")
        crud.update_user_task_name(user_task.id, task_name)


async def checking_online_task(mpets, user, user_task):
    profile = await mpets.view_profile(user.pet_id)
    if not profile["status"]:
        return 0
    if profile["last_login"] == "online":
        task_name = user_task.task_name
        if int(task_name.split("_")[1]) == 0:
            task_name = "30online_" + str(int(time.time()))
            crud.update_user_task_name(user_task.id, task_name)
            return 0
        else:
            task_name = int(task_name.split("_")[1])
            left_time = time.time() - task_name
            if left_time >= 1800:
                crud.update_user_task(user_task.id, user_task.end, "completed")
                await functions.add_user_points(user_id=user.user_id,
                                                task_name="30online")
            else:
                left_time = int(left_time // 60)
                crud.update_user_task(user_task.id, left_time, "waiting")
    else:
        crud.update_user_task(user_task.id, 0, "waiting")
        crud.update_user_task_name(user_task.id, "30online_0")


async def checking_inOnline_task(mpets, user, user_task):
    profile = await mpets.view_profile(user.pet_id)
    if not profile["status"]:
        return 0
    if profile["last_login"] == "online":
        task_name = user_task.task_name
        h, m = task_name.split("_")[-1].split(":")
        current_date = time.strftime("%d %b %Y", time.gmtime(time.time()))
        current_date += f' {h}:{m}'
        unix_time = int(time.mktime(time.strptime(current_date, '%d %b %Y '
                                                                '%H:%M')))
        if unix_time - 120 <= int(time.time()) <= unix_time + 120:
            crud.update_user_task(user_task.id, user_task.end, "completed")
            await functions.add_user_points(user_id=user.user_id,
                                            task_name="online")
    else:
        # timeout
        pass


async def checking_getGift_utask(mpets, user, user_task):
    gift_id = user_task.task_name.split("_")[-1]
    pet_gift = False
    if gift_id.isdigit() is False:
        return 0
    gifts = await mpets.view_gifts(user.pet_id)
    if int(gift_id) == 0:
        for gift in gifts["players"]:
            if "сегодня" in gift["date"]:
                pet_gift = True
        if pet_gift:
            crud.update_user_task(user_task.id, user_task.end, "completed")
            await functions.add_user_points(user_id=user.user_id,
                                            task_name="get_gift")
    else:
        gift_id = int(gifts_name[int(gift_id) - 1][0])
        for gift in gifts["players"]:
            if gift_id in [26, 27, 35]:
                if gift["pet_id"]:
                    try:
                        if "сегодня" in gift["date"] and \
                                (int(gift["present_id"]) == 36 or
                                 int(gift["present_id"]) == 26):
                            pet_gift = True
                        elif "сегодня" in gift["date"] and \
                                (int(gift["present_id"]) == 37 or
                                 int(gift["present_id"]) == 27):
                            pet_gift = True
                        elif "сегодня" in gift["date"] and \
                                (int(gift["present_id"]) == 35 or
                                 int(gift["present_id"]) == 38):
                            pet_gift = True
                    except Exception:
                        pass
            else:
                if gift["pet_id"]:
                    try:
                        if "сегодня" in gift["date"] and \
                                int(gift["present_id"]) == int(gift_id):
                            pet_gift = True
                    except Exception:
                        pass
        if pet_gift:
            crud.update_user_task(user_task.id, user_task.end, "completed")
            await functions.add_user_points(user_id=user.user_id,
                                            task_name="get_gift")


async def checking_sendGift_utask(mpets, user, user_task, pet_id):
    gift_id = user_task.task_name.split("_")[-1]
    pet_gift = False
    if gift_id.isdigit() is False:
        return 0
    gifts = await mpets.view_gifts(pet_id)
    if int(gift_id) == 0:
        for gift in gifts["players"]:
            if gift["pet_id"]:
                try:
                    if user.pet_id == int(gift["pet_id"]) and \
                            "сегодня" in gift["date"]:
                        pet_gift = True
                except Exception:
                    pass
        if pet_gift:
            crud.update_user_task(user_task.id, user_task.end, "completed")
            await functions.add_user_points(user_id=user.user_id,
                                            task_name=user_task.task_name)
            return True
    else:
        gift_id = int(gifts_name[int(gift_id) - 1][0])
        for gift in gifts["players"]:
            if gift_id in [26, 27, 35]:
                if gift["pet_id"]:
                    try:
                        if "сегодня" in gift["date"] and \
                                (int(gift["present_id"]) == 36 or
                                 int(gift["present_id"]) == 26) and \
                                user.pet_id == int(gift["pet_id"]):
                            pet_gift = True
                        elif "сегодня" in gift["date"] and \
                                (int(gift["present_id"]) == 37 or
                                 int(gift["present_id"]) == 27) and \
                                user.pet_id == int(gift["pet_id"]):
                            pet_gift = True
                        elif "сегодня" in gift["date"] and \
                                (int(gift["present_id"]) == 35 or
                                 int(gift["present_id"]) == 38) and \
                                user.pet_id == int(gift["pet_id"]):
                            pet_gift = True
                    except Exception:
                        pass
            else:
                if gift["pet_id"]:
                    try:
                        if "сегодня" in gift["date"] and \
                                int(gift["present_id"]) == gift_id and \
                                user.pet_id == int(gift["pet_id"]):
                            pet_gift = True
                    except Exception:
                        pass
        if pet_gift:
            crud.update_user_task(user_task.id, user_task.end, "completed")
            await functions.add_user_points(user_id=user.user_id,
                                            task_name=user_task.task_name)
            return True


async def start_verify_user(user, cookies):
    today = int(datetime.today().strftime("%Y%m%d"))
    user_tasks = crud.get_user_tasks(user.user_id, today)
    '''user_bot = crud.get_bot(user.user_id)
    if user_bot is None:
        mpets = MpetsApi()
        resp = await mpets.start()
        if resp["status"] == "ok":
            user_bot = crud.create_bot(user.user_id, resp["pet_id"],
                                       resp["name"], resp["password"])
        else:
            log = logger.bind(context=f"account {resp}")
            log.warning(f"Ошибка при создании бота. Пользователь:"
                        f" {user.user_id}")
            return False
    if not user_tasks:
        return False
    mpets = MpetsApi(user_bot.name, user_bot.password)
    resp = await mpets.login()
    if resp["status"] != "ok":
        log = logger.bind(context=f"account {resp}")
        log.warning(f"Ошибка при авторизации бота. Пользователь:"
                    f" {user.user_id}")
        mpets = MpetsApi()
        resp = await mpets.start()
        if resp["status"] == "ok":
            user_bot = crud.update_bot(user.user_id, resp["pet_id"],
                                       resp["name"], resp["password"])
        else:
            log = logger.bind(context=f"account {resp}")
            log.warning(f"Ошибка при создании бота. Пользователь:"
                        f" {user.user_id}")
            return False
    mpets = MpetsApi(user_bot.name, user_bot.password)
    resp = await mpets.login()
    if resp["status"] != "ok":
        log = logger.bind(context=f"account {resp}")
        log.warning(f"Ошибка при авторизации бота. Пользователь:"
                    f" {user.user_id}")
        mpets = MpetsApi()
        await mpets.start()'''
    mpets = MpetsApi(cookies=cookies)
    # await mpets.start()
    for user_task in user_tasks:
        try:
            if user_task.status == "completed":
                continue
            elif user_task.status == "timeout":
                continue
            elif "avatar" in user_task.task_name:
                await checking_avatar_task(mpets, user, user_task)
            elif "anketa" in user_task.task_name:
                await checking_anketa_task(mpets, user, user_task)
            elif "30online" in user_task.task_name:
                await checking_online_task(mpets, user, user_task)
            elif "in_online" in user_task.task_name:
                await checking_inOnline_task(mpets, user, user_task)
            elif "get_gift" in user_task.task_name or \
                    "get_random_gift" in user_task.task_name:
                await checking_getGift_utask(mpets, user, user_task)
        except Exception as e:
            logger.error(f"start_verify_user {user.user_id}"
                         f"task {user_task.task_name}"
                         f"error {e}")


async def checking_users_tasks():
    logger.debug("start checking_users_tasks")
    mpets_sessions = []
    for i in range(8):
        mpets = MpetsApi()
        r = await mpets.start()
        if r['status']:
            mpets_sessions.append(r['cookies'])
    while True:
        try:
            users = crud.get_users_with_status("ok")
            tasks, counter = [], 0
            time0 = int(time.time())
            for i in range(0, len(users)):
                user = users[i]
                today = int(datetime.today().strftime("%Y%m%d"))
                user_tasks = crud.get_user_tasks(user.user_id, today)
                if not user_tasks:
                    continue
                task = asyncio.create_task(start_verify_user(user,
                                                             mpets_sessions[
                                                                 random.randint(0, len(mpets_sessions) - 1)]))
                tasks.append(task)
                if len(tasks) >= 5:
                    await asyncio.gather(*tasks)
                    await asyncio.sleep(1)
                    tasks = []
                elif i + 1 == len(users):
                    await asyncio.gather(*tasks)
                    await asyncio.sleep(1)
                    tasks = []
            total_time = int(time.time() - time0)
            crud.health(usertasks=total_time)
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(e)
            await asyncio.sleep(10)


async def creating_club_tasks():
    logger.debug("start creating_club_tasks")
    settings = get_settings()
    while True:
        try:
            today = int(datetime.today().strftime("%Y%m%d"))
            user_tasks = crud.get_club_tasks_all(today, "generation")
            for user_task in user_tasks:
                user = crud.get_user(user_id=user_task.user_id)
                club = crud.get_club(club_id=user.club_id)
                mpets = await get_mpets_api(club=club, api_key=settings.api_key)
                await functions.creation_club_tasks(user_task, mpets)
            await asyncio.sleep(3)
        except Exception as e:
            # raise
            logger.error(f"Ошибка при создании задания {e}")
            await asyncio.sleep(10)


async def checking_thread():
    logger.debug("start checking_thread")
    mpets = MpetsApi()
    await mpets.start()
    thread_id, page = 2600581, 1
    while True:
        try:
            thread = await mpets.thread(thread_id, page)
            for msg in thread['messages']:
                if crud.get_message(thread_id=thread_id,
                                    message_id=msg['message_id']):
                    continue
                user = crud.get_user_pet_id(msg['pet_id'])
                if user is None:
                    crud.create_play_message(pet_id=msg['pet_id'],
                                             thread_id=thread_id,
                                             message_id=msg['message_id'],
                                             page=page)
                    continue
                last_msg = crud.get_message(thread_id=thread_id,
                                            message_id=int(msg['message_id']) - 1)
                if last_msg is None:
                    pass
                else:
                    if last_msg.pet_id == user.pet_id:
                        crud.create_play_message(pet_id=msg['pet_id'],
                                                 thread_id=thread_id,
                                                 message_id=msg['message_id'],
                                                 page=page)
                        continue
                today = int(datetime.today().strftime("%Y%m%d"))
                user_tasks = crud.get_club_tasks(user.user_id, today, "waiting")
                for task in user_tasks:
                    if task.task_name != "play":
                        continue
                    await check_task(user, task, task.progress + 1, "play")
                crud.create_play_message(pet_id=msg['pet_id'],
                                         thread_id=thread_id,
                                         message_id=msg['message_id'],
                                         page=page)
            if len(thread['messages']) == 15:
                page += 1
            await asyncio.sleep(3)
        except Exception as e:
            pass


async def update_charm_rating():
    logger.debug("start update_charm_rating")
    mpets = MpetsApi()
    await mpets.start()
    page = 1
    time0 = time.time()
    while True:
        try:
            game_time = await mpets.game_time()
            if not game_time["status"]:
                await asyncio.sleep(5)
                continue
            if int(game_time["time"].split(":")[1]) % 10 == 0:
                await asyncio.sleep(5)
                continue
            resp = await mpets.best("charm", page)
            # elapsed_time = time.time() - time0
            # logger.info(f"запрос выполнился за | {elapsed_time}")
            if not resp["status"]:
                continue
            for pet in resp["pets"]:
                top = crud.get_charm_place(place=pet["place"])
                if top is None:
                    crud.create_charm_rating(pet_id=pet["pet_id"],
                                             place=pet["place"],
                                             score=pet["beauty"])
                    continue
                today = int(datetime.today().strftime("%Y%m%d"))
                user = crud.get_user_pet_id(pet_id=pet["pet_id"])
                if user is None:
                    crud.update_charm_place(pet_id=pet["pet_id"],
                                            place=pet["place"],
                                            score=pet["beauty"])
                    continue
                user_task = crud.get_user_task_name(user_id=user.user_id,
                                                    task_name="charm",
                                                    today=today)
                if user_task is None:
                    crud.update_charm_place(pet_id=pet["pet_id"],
                                            place=pet["place"],
                                            score=pet["beauty"])
                    continue
                elif user_task.status == "completed":
                    continue
                else:
                    # если разность больше 0, то игрок должен набрать еще рейтинга
                    difference = user_task.end - int(pet["score"])
                    if difference > 0:
                        end = 0
                        # количество очков меньше, чем нужно
                        if user_task.progress < int(pet["score"]):
                            # количество очков увеличилось
                            a = int(pet["score"]) - user_task.progress
                            progress = user_task.progress + a
                        else:
                            # количество очков уменьшилось
                            progress = int(pet["score"])
                            end = progress + 30
                        crud.update_user_task(id=user_task.id,
                                              progress=progress)
                        if end != 0:
                            crud.update_user_task_end(id=user_task.id,
                                                      end=end)
                    else:
                        crud.update_user_task(id=user_task.id,
                                              progress=user_task.end,
                                              status="completed")
                        await functions.add_user_points(user_id=user.user_id,
                                                        task_name="charm")
                    crud.update_charm_place(pet_id=pet["pet_id"],
                                            place=pet["place"],
                                            score=pet["beauty"])
            page += 1
            if page >= 668:
                elapsed_time = int(time.time() - time0)
                crud.health(charm=elapsed_time)
                page = 1
                time0 = time.time()
                await asyncio.sleep(1)
        except Exception:
            pass


async def update_races_rating():
    logger.debug("start update_races_rating")
    mpets = MpetsApi()
    await mpets.start()
    page = 1
    time0 = time.time()
    while True:
        try:
            game_time = await mpets.game_time()
            if not game_time["status"]:
                continue
            if int(game_time["time"].split(":")[1]) % 10 == 0:
                continue
            resp = await mpets.best("races", page)
            if not resp["status"]:
                continue
            for pet in resp["pets"]:
                top = crud.get_races_place(place=pet["place"])
                if top is None:
                    crud.create_races_rating(pet_id=pet["pet_id"],
                                             place=pet["place"],
                                             score=pet["beauty"])
                    continue
                today = int(datetime.today().strftime("%Y%m%d"))
                user = crud.get_user_pet_id(pet_id=pet["pet_id"])
                if user is None:
                    crud.update_races_place(pet_id=pet["pet_id"],
                                            place=pet["place"],
                                            score=pet["beauty"])
                    continue
                user_task = crud.get_user_task_name(user_id=user.user_id,
                                                    task_name="races",
                                                    today=today)
                if user_task is None:
                    continue
                elif user_task.status == "completed":
                    continue
                else:
                    difference = user_task.end - int(pet["score"])
                    if difference > 0:
                        end = 0
                        # количество очков меньше, чем нужно
                        if user_task.progress < int(pet["score"]):
                            # количество очков увеличилось
                            a = int(pet["score"]) - user_task.progress
                            progress = user_task.progress + a
                        else:
                            # количество очков уменьшилось
                            progress = int(pet["score"])
                            end = progress + 30
                        crud.update_user_task(id=user_task.id,
                                              progress=progress)
                        if end != 0:
                            crud.update_user_task_end(id=user_task.id,
                                                      end=end)
                    else:
                        crud.update_user_task(id=user_task.id,
                                              progress=user_task.end,
                                              status="completed")
                        await functions.add_user_points(user_id=user.user_id,
                                                        task_name="races")
                    crud.update_charm_place(pet_id=pet["pet_id"],
                                            place=pet["place"],
                                            score=pet["beauty"])
            page += 1
            if page >= 668:
                elapsed_time = int(time.time() - time0)
                crud.health(races=elapsed_time)
                page = 1
                time0 = time.time()
                await asyncio.sleep(1)
        except Exception:
            pass


async def checking_avatar_htask(mpets, user, user_task):
    today = int(datetime.today().strftime("%m%d"))
    avatar_ids = []
    if holiday_1402[0] <= today <= holiday_1402[1]:
        prize = holiday_1402_prizes['avatar']
        avatar_ids = [4, 8]
    elif holiday_2302[0] <= today <= holiday_2302[1]:
        prize = holiday_2302_prizes['avatar']
        avatar_ids = [6, 7]
    elif holiday_308[0] <= today <= holiday_308[1]:
        prize = holiday_308_prizes['avatar']
        avatar_ids = [0, 1]
    elif holiday_401[0] <= today <= holiday_401[1]:
        prize = holiday_401_prizes['avatar']
        avatar_ids = [5, 0]
    elif holiday_501[0] <= today <= holiday_501[1]:
        prize = holiday_501_prizes['avatar']
        avatar_ids = [1, 0]
    profile = await mpets.view_profile(user.pet_id)
    if profile["status"] != "ok":
        return 0
    task_name = user_task.task_name
    avatar_id = user_task.task_name.split("_")[-1]
    avatar_id = avatar_id.rsplit(":", maxsplit=1)[0]
    if int(profile["ava_id"]) in avatar_ids:
        ava = task_name.split("_", maxsplit=1)[-1]
        start_time = ava.rsplit(":", maxsplit=1)[1]
        if int(start_time) == 0:
            task_name = f"avatar_{avatar_id}:{int(time.time())}"
            crud.update_user_task_name(user_task.id, task_name)
        else:
            left_time = time.time() - int(start_time)
            if left_time >= 86400:
                crud.update_user_task(user_task.id, user_task.end, "completed")
                crud.add_rewards(user_id=user.user_id, points=2, personal_tasks=1, club_tasks=1)
            else:
                left_time = int(left_time // 60 // 60)
                crud.update_user_task(user_task.id, left_time, "waiting")
    else:
        task_name = f"avatar_{avatar_id}:0"
        crud.update_user_task(user_task.id, 0, "waiting")
        crud.update_user_task_name(user_task.id, task_name)


async def checking_anketa_htask(mpets, user, user_task):
    try:
        today = int(datetime.today().strftime("%m%d"))
        smiles = []
        if holiday_1402[0] <= today <= holiday_1402[1]:
            prize = holiday_1402_prizes['anketa']
            smiles = ["❤", "❤️", "♥️"]
        elif holiday_2302[0] <= today <= holiday_2302[1]:
            prize = holiday_2302_prizes['anketa']
            smiles = ["⭐️", "⭐"]
        elif holiday_308[0] <= today <= holiday_308[1]:
            prize = holiday_308_prizes['anketa']
            smiles = ["✿ܓ"]
        elif holiday_401[0] <= today <= holiday_401[1]:
            prize = holiday_401_prizes['anketa']
            smiles = ["Никому не верю"]
        elif holiday_501[0] <= today <= holiday_501[1]:
            prize = holiday_501_prizes['anketa']
            smiles = ["Мир, труд, май! ✿", "Мир, труд, май!✿"]
        profile = await mpets.view_anketa(user.pet_id)
        if profile["status"] != "ok":
            return False
        task_name = user_task.task_name
        anketa_about = task_name.split("_", maxsplit=1)[-1]
        anketa_about = anketa_about.rsplit(":", maxsplit=1)[0]
        if profile["about"] in smiles or profile["ank"] in smiles:
            ank = task_name.split("_", maxsplit=1)[-1]
            start_time = ank.rsplit(":", maxsplit=1)[1]
            if int(start_time) == 0:
                task_name = f"anketa_{anketa_about}:{int(time.time())}"
                crud.update_user_task_name(user_task.id, task_name)
            else:
                left_time = time.time() - int(start_time)
                # logger.debug(f"left_time {left_time}")
                if left_time >= 86400:
                    crud.update_user_task(user_task.id, user_task.end, "completed")
                    crud.add_rewards(user_id=user.user_id, points=2, personal_tasks=1, club_tasks=1)
                else:
                    left_time = int(left_time // 60 // 60)
                    crud.update_user_task(user_task.id, left_time, "waiting")
        else:
            task_name = f"anketa_{anketa_about}:0"
            crud.update_user_task(user_task.id, 0, "waiting")
            crud.update_user_task_name(user_task.id, task_name)
    except Exception as e:
        logger.error(f"checking_anketa_htask {user.user_id} "
                     f"error {e}")


async def checking_exchangeGifts_htask(mpets, user, user_task, date):
    progress = user_task.progress
    page = 1
    today = True
    gift_ids = []
    if holiday_1402[0] <= date <= holiday_1402[1]:
        hdate = holiday_1402[2]
        prize = holiday_1402_prizes['gifts']
        gift_ids = [11, 34]
    elif holiday_2302[0] <= date <= holiday_2302[1]:
        hdate = holiday_2302[2]
        prize = holiday_2302_prizes['gifts']
        gift_ids = [26, 27, 35]
    elif holiday_308[0] <= date <= holiday_308[1]:
        hdate = holiday_308[2]
        prize = holiday_308_prizes['gifts']
        gift_ids = [45, 46, 47]
    elif holiday_401[0] <= date <= holiday_401[1]:
        hdate = holiday_401[2]
        prize = holiday_401_prizes['gifts']
        gift_ids = [32, 33]
    elif holiday_501[0] <= date <= holiday_501[1]:
        hdate = holiday_501[2]
        prize = holiday_501_prizes['gifts']
        gift_ids = [2, 45]
    while True:
        if today is False:
            break
        today = False
        gifts = await mpets.view_gifts(user.pet_id, page)
        try:
            g = gifts["players"]
        except:
            logger.error(f"user {user.user_id} {gifts}")
        for gift in gifts["players"]:
            if ("вчера" in gift["date"] or "сегодня" in gift["date"]) \
                    and int(gift["present_id"]) in gift_ids:
                today = True
                if gift["pet_id"] is None:
                    continue
                for ipage in range(1, 5):
                    leave = True
                    another_gifts = await mpets.view_gifts(gift["pet_id"], ipage)
                    try:
                        g = another_gifts["players"]
                    except:
                        logger.error(f"user {user.user_id} {another_gifts}")
                    for g in another_gifts["players"]:
                        if g["pet_id"] is None:
                            continue
                        if "вчера" in g["date"] or "сегодня" in g["date"]:
                            leave = False
                        if ("вчера" in g["date"] or "сегодня" in g["date"]) \
                                and int(g["present_id"]) in gift_ids and int(g["pet_id"]) == user.pet_id:
                            if crud.get_pet_pair(pet_id=user.pet_id,
                                                 friend_id=gift["pet_id"],
                                                 date=hdate) is None:
                                crud.create_gift_pair(pet_id=user.pet_id,
                                                      friend_id=gift["pet_id"],
                                                      present_id=gift["present_id"],
                                                      date=hdate)
                                progress += 1
                    if leave:
                        break
        page += 1
    if progress < user_task.end:
        crud.update_user_task(user_task.id, progress, "waiting")
    else:
        crud.update_user_task(user_task.id, user_task.end, "completed")
        crud.add_rewards(user_id=user.user_id, points=2, personal_tasks=1, club_tasks=1)


async def start_checking_holiday_tasks(user, date):
    user_tasks = crud.get_user_tasks(user.user_id, date)
    user_bot = crud.get_bot(user.user_id)
    if user_bot is None:
        mpets = MpetsApi()
        resp = await mpets.start()
        if resp["status"] == "ok":
            user_bot = crud.create_bot(user.user_id, resp["pet_id"],
                                       resp["name"], resp["password"])
        else:
            log = logger.bind(context=f"account {resp}")
            log.warning(f"Ошибка при создании бота. Пользователь:"
                        f" {user.user_id}")
            return False
    if not user_tasks:
        return False
    mpets = MpetsApi(user_bot.name, user_bot.password)
    resp = await mpets.login()
    if resp["status"] != "ok":
        log = logger.bind(context=f"account {resp}")
        log.warning(f"Ошибка при авторизации бота. Пользователь:"
                    f" {user.user_id}")
        mpets = MpetsApi()
        resp = await mpets.start()
        if resp["status"] == "ok":
            user_bot = crud.update_bot(user.user_id, resp["pet_id"],
                                       resp["name"], resp["password"])
        else:
            log = logger.bind(context=f"account {resp}")
            log.warning(f"Ошибка при создании бота. Пользователь:"
                        f" {user.user_id}")
            return False
    mpets = MpetsApi(user_bot.name, user_bot.password)
    resp = await mpets.login()
    if resp["status"] != "ok":
        log = logger.bind(context=f"account {resp}")
        log.warning(f"Ошибка при авторизации бота. Пользователь:"
                    f" {user.user_id}")
        mpets = MpetsApi()
        await mpets.start()
    for user_task in user_tasks:
        try:
            if user_task.status == "completed":
                continue
            elif user_task.status == "timeout":
                continue
            elif "avatar" in user_task.task_name:
                await checking_avatar_htask(mpets, user, user_task)
            elif "anketa" in user_task.task_name:
                await checking_anketa_htask(mpets, user, user_task)
            elif "gifts" in user_task.task_name:
                await checking_exchangeGifts_htask(mpets, user, user_task, date)
        except Exception as e:
            logger.error(f"start_checking_holiday_tasks {user.user_id} "
                         f"task {user_task.task_name} "
                         f"error {e}")


async def checking_holiday_tasks():
    logger.debug("start checking_holiday_tasks")
    while True:
        try:
            today = int(datetime.today().strftime("%m%d"))
            if holiday_1402[0] <= today <= holiday_1402[1]:
                date = holiday_1402[2]
            elif holiday_2302[0] <= today <= holiday_2302[1]:
                date = holiday_2302[2]
            elif holiday_308[0] <= today <= holiday_308[1]:
                date = holiday_308[2]
            elif holiday_401[0] <= today <= holiday_401[1]:
                date = holiday_401[2]
            elif holiday_501[0] <= today <= holiday_501[1]:
                date = holiday_501[2]
            else:
                await asyncio.sleep(120)
                continue
            users = crud.get_users_with_status(status="ok")
            tasks, counter = [], 0
            for i in range(0, len(users)):
                user = users[i]
                user_tasks = crud.get_user_tasks(user_id=user.user_id, today=date)
                if not user_tasks:
                    continue
                task = asyncio.create_task(start_checking_holiday_tasks(user=user, date=date))
                tasks.append(task)
                if len(tasks) >= 10:
                    await asyncio.gather(*tasks)
                    await asyncio.sleep(1)
                    tasks = []
                elif i + 1 == len(users):
                    await asyncio.gather(*tasks)
                    await asyncio.sleep(1)
                    tasks = []
            await asyncio.gather(*tasks)
            await asyncio.sleep(1)
            tasks = []
        except Exception as e:
            logger.error(e)
            await asyncio.sleep(10)


def get_next_user(users):
    for user in users:
        yield user


async def get_wipe_text_user_rating():
    counter, hidden = 1, False
    top_users_stats = crud.get_users_stats_order_by_points(limit=30)
    text = "🧑‍ Рейтинг игроков \n\n"
    if not top_users_stats:
        return "Рейтинг пуст"
    users = get_next_user(users=top_users_stats)
    last_points = None
    while counter <= 10:
        try:
            user_stats = next(users)
        except StopIteration as e:
            break

        top_user = crud.get_user(user_stats.user_id)
        if last_points is None:
            # Если в рейтинге есть пользователь с 50 очков и более,
            # то активируется более "продвинутый" рейтинг.
            if user_stats.points <= 49:
                last_points = None
            else:
                last_points = user_stats.points
            text += f"{counter}. {top_user.name} ( {top_user.user_id} ) — {user_stats.points} 🏅\n"
            counter += 1
        elif last_points == user_stats.points:
            last_points = user_stats.points
            text += f"  {top_user.name} ( {top_user.user_id} ) — {user_stats.points} 🏅\n"
        else:
            last_points = user_stats.points
            text += f"{counter}. {top_user.name} ( {top_user.user_id} ) — {user_stats.points} 🏅\n"
            counter += 1
    return text


async def get_wipe_text_club_rating():
    counter = 1
    clubs = crud.get_clubs_stats_order_by_points()
    text = "🏠 Рейтинг клубов.\n\n"
    if not clubs:
        return "❗ Рейтинг пуст."
    for club_stats in clubs:
        club = crud.get_club(club_stats.club_id)
        text += f"{counter}. {club.name} ( {club.club_id} ) — {club_stats.total_tasks} ⛱/" \
                f"{club_stats.points}🎈\n"
        counter += 1
    return text


async def wipe():
    wipe = False
    while True:
        today = int(datetime.today().strftime("%m%d"))
        if wipe is True:
            await asyncio.sleep(3600)
            continue
        if today == 823:
            notice(await get_wipe_text_user_rating())
            notice(await get_wipe_text_club_rating())
            crud.wipe()
            wipe = True
        await asyncio.sleep(10)