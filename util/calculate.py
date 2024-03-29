from typing import Optional
from unittest import result

from bson import ObjectId
from database import db
from util.get_class import get_user_classname


async def calculate_awards(
    user: str,
    trophies: list[dict] = [],
    activities: list[dict] = [],
    full: float = 10.0,
) -> dict[str, float]:
    # Read trophy list with `members` field (array) containing user's id (._id field in members)

    inject_trophies = [
        {
            "$match": {
                "members._id": user,
            }
        },
        {
            "$project": {
                "members": {
                    "$filter": {
                        "input": "$members",
                        "as": "member",
                        "cond": {
                            "$and": [
                                {"$eq": ["$$member._id", user]},
                                {"$eq": ["$$member.status", "effective"]},
                            ]
                        },
                    }
                },
                "awards": True,
                "award": True,
            }
        },
    ]

    trophies = await db.zvms.trophies.aggregate(inject_trophies).to_list(None)

    inject_activities = [
        {
            "$match": {
                "members._id": user,
                "type": "special",
                "special.classify": "prize",
            }
        },
        {
            "$project": {
                "members": {
                    "$filter": {
                        "input": "$members",
                        "as": "member",
                        "cond": {"$eq": ["$$member._id", user]},
                    }
                },
            }
        },
    ]
    activities = await db.zvms.activities.aggregate(inject_activities).to_list(None)

    awards = {
        "on-campus": 0.0,
        "off-campus": 0.0,
        "total": 0.0,
    }
    for activity in activities:
        if len(activity["members"]) == 0:
            continue
        member = activity["members"][0]
        if member["_id"] == user:
            if member["mode"] == "on-campus":
                awards["on-campus"] += member["duration"]
            elif member["mode"] == "off-campus":
                awards["off-campus"] += member["duration"]
            awards["total"] += member["duration"]

    if awards["total"] >= full:
        # Average the duration of recorded time as time limit is reached
        awards["on-campus"] = round(awards["on-campus"] / awards["total"] * full, 1)
        awards["off-campus"] = full - awards["on-campus"]
        awards["total"] = full
        return awards

    # Calculate awards
    for trophy in trophies:
        if len(trophy["members"]) == 0:
            continue
        member = trophy["members"][0]
        award_name = trophy["award"]
        for award in trophy["awards"]:
            if award["name"] == award_name:
                flag_ = False
                duration = award["duration"]
                if awards["total"] + award["duration"] > full:
                    duration = full - awards["total"]
                    flag_ = True
                if member["mode"] == "on-campus":
                    awards["on-campus"] += duration
                elif member["mode"] == "off-campus":
                    awards["off-campus"] += duration
                else:
                    break
                if flag_:
                    return awards
                awards["total"] += award["duration"]
                break
    return awards


async def calculate_special_activities(
    user: str, activities: Optional[list[dict]] = []
) -> dict[str, float]:
    # Read user's activity list
    inject = [
        {
            "$match": {
                "members._id": user,
                "type": "special",
                "status": "effective",
                "members.status": "effective",
                "special.classify": {"$ne": "prize"},
            }
        },
        {
            "$project": {
                "members": {
                    "$filter": {
                        "input": "$members",
                        "as": "member",
                        "cond": {"$eq": ["$$member._id", user]},
                    }
                }
            }
        },
    ]
    activities = await db.zvms.activities.aggregate(inject).to_list(None)

    result = {
        "on-campus": 0.0,
        "off-campus": 0.0,
        "social-practice": 0.0,
    }

    if activities is None:
        return result

    for activity in activities:
        if len(activity["members"]) == 0:
            continue
        member = activity["members"][0]
        if member["mode"] == "on-campus":
            result["on-campus"] += member["duration"]
        elif member["mode"] == "off-campus":
            result["off-campus"] += member["duration"]
        else:
            result["social-practice"] += member["duration"]

    return result


async def calculate_normal_activities(
    user: str, activities: Optional[list[dict]] = []
) -> dict[str, float]:
    # Read user's activity list

    inject = [
        {
            "$match": {
                "members._id": user,
                "status": "effective",
                "members.status": "effective",
                "type": {"$ne": "special"},
            }
        },
        {
            "$project": {
                "members": {
                    "$filter": {
                        "input": "$members",
                        "as": "member",
                        "cond": {
                            "$and": [
                                {"$eq": ["$$member._id", user]},
                                {"$eq": ["$$member.status", "effective"]},
                            ]
                        },
                    }
                }
            }
        },
    ]
    activities = await db.zvms.activities.aggregate(inject).to_list(None)

    result = {
        "on-campus": 0.0,
        "off-campus": 0.0,
        "social-practice": 0.0,
    }

    if activities is None:
        return result

    for activity in activities:
        if len(activity["members"]) == 0:
            continue
        member = activity["members"][0]
        if member["mode"] == "on-campus":
            result["on-campus"] += member["duration"]
        elif member["mode"] == "off-campus":
            result["off-campus"] += member["duration"]
        else:
            result["social-practice"] += member["duration"]

    return result


async def calculate_time(
    user: str,
    normal_activities: list[dict] = [],
    special_activities: list[dict] = [],
    prize_activities: list[dict] = [],
    trophies: list[dict] = [],
    prize_full: float = 10.0,
    discount: bool = False,
    discount_rate: float = 1 / 3,
    discount_full: float = 6.0,  # if `on-campus` is full, can be used to calculate `off-campus` time with 1/3 exceeded time (rounded to 1 decimal place)
    discount_base: float = 30.0,  # if `on-campus` is full, can be used to calculate `off-campus` time with 1/3 exceeded time (rounded to 1 decimal place)
) -> dict[str, float]:
    result = {
        "on-campus": 0.0,
        "off-campus": 0.0,
        "social-practice": 0.0,
        "trophy": 0.0,
        "total": 0.0,
    }
    trophy = await calculate_awards(user)
    result["on-campus"] = trophy["on-campus"]
    result["off-campus"] = trophy["off-campus"]
    result["total"] = trophy["total"]
    result["trophy"] = trophy["total"]
    normal = await calculate_normal_activities(user)
    result["on-campus"] += normal["on-campus"]
    result["off-campus"] += normal["off-campus"]
    result["social-practice"] += normal["social-practice"]
    result["total"] += (
        normal["on-campus"] + normal["off-campus"] + normal["social-practice"]
    )
    special = await calculate_special_activities(user)
    result["on-campus"] += special["on-campus"]
    result["off-campus"] += special["off-campus"]
    result["social-practice"] += special["social-practice"]
    result["total"] += (
        special["on-campus"] + special["off-campus"] + special["social-practice"]
    )
    result["on-campus"] = round(result["on-campus"], 1)
    result["off-campus"] = round(result["off-campus"], 1)
    if discount:
        if result["on-campus"] > discount_base:
            discount_duration = round(
                (result["on-campus"] - discount_base) * discount_rate, 1
            )
            if discount_duration > discount_full:
                discount_duration = discount_full
            result["off-campus"] += discount_duration
    result["social-practice"] = round(result["social-practice"], 1)
    result["trophy"] = round(result["trophy"], 1)
    result["total"] = round(result["total"], 1)
    return result
