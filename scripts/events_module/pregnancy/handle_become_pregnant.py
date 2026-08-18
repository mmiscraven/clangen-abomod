from random import randint, choice, choices
from typing import Optional, List

import i18n

from scripts.cat.cats import Cat
from scripts.clan_package.settings import get_clan_setting
from scripts.event_class import Single_Event
from scripts.events_module.pregnancy.build_strings import (
    get_pregnancy_strings,
)
from scripts.events_module.pregnancy.create_kits import get_amount_of_kits, get_kits
from scripts.events_module.text_adjust import event_text_adjust
from scripts.game_structure import game


def handle_zero_moon_pregnant(cat: Cat, other_cat: Optional[Cat] = None):
    """Handles if the cat is zero moons pregnant."""
    if other_cat and not other_cat.status.alive_in_player_clan:
        return

    if (cat.ID in game.clan.pregnancy_data):
        return

    # male cats can get pregnant with this setting, so we don't bother to check gender here
    if not other_cat and randint(0, 1):
        _retrieve_secret_kittens(cat)
        return

    pregnant_cat = cat
    second_parent = other_cat
    _create_pregnancy_data(pregnant_cat, second_parent)
    _handle_pregnancy_notice(pregnant_cat, second_parent)

    return


def _handle_pregnancy_notice(pregnant_cat, second_parent):
    allow_affair = get_clan_setting("affair")
    allow_coparenting = get_clan_setting("unmated parentage")

    mate = []

    mate = [
        Cat.fetch_cat(mate_id)
        for mate_id in pregnant_cat.mate
        if Cat.fetch_cat(mate_id)
    ]

    # Second parent is one of the pregnant cat's mates:
    # normal pregnancy announcement
    if second_parent and second_parent.ID in pregnant_cat.mate:
        text, involved_cats = _create_pregnancy_announcement(
            pregnant_cat, "announcement", random_cat=second_parent,
    )
    # Pregnant cat has no mate:
    # surprise/unmated pregnancy
    elif allow_coparenting and not mate:
        text, involved_cats = _create_pregnancy_announcement(
            pregnant_cat, "announcement_surprise",
        )
    # Pregnant cat has a mate, but the second parent is somebody else:
    # possible affair
    elif (
        allow_affair is True
        and second_parent
        and second_parent.ID not in pregnant_cat.mate
        and mate
    ):
        announcement_key = choice(["announcement_affair", "announcement"])
        _set_affair_visibility(pregnant_cat, announcement_key == "announcement_affair")
        random_cat = mate[0]
        text, involved_cats = _create_pregnancy_announcement(
            pregnant_cat, announcement_key, random_cat=random_cat
        )
    # if all else fails, just a regular announcement happens
    else:
        text, involved_cats = _create_pregnancy_announcement(
            pregnant_cat, "announcement", random_cat=second_parent
        )
    game.cur_events_list.append(Single_Event(text, "birth_death", involved_cats))


def _create_pregnancy_data(pregnant_cat: Cat, second_parent: Optional[Cat]):
    """Creates the pregnancy data entry for a new pregnancy."""
    game.clan.pregnancy_data[pregnant_cat.ID] = {
        "second_parent": str(second_parent.ID) if second_parent else None,
        "moons": 0,
        "amount": 0,
    }


def _retrieve_secret_kittens(cat):
    amount = get_amount_of_kits(cat)
    kits = get_kits(amount, cat, None)
    print_event = i18n.t(
        "conditions.pregnancy.pregnant_secret",
        name=cat.name,
        insert=i18n.t("conditions.pregnancy.kit_amount", count=amount),
    )
    cats_involved = [cat.ID]
    for kit in kits:
        cats_involved.append(kit.ID)
    game.cur_events_list.append(
        Single_Event(print_event, "birth_death", cats_involved, cat_dict={"m_c": cat})
    )


def _create_pregnancy_announcement(
    pregnant_cat: Cat,
    announcement_key: str,
    random_cat: Optional[Cat] = None,
    mentioned_cat: Optional[Cat] = None,
):
    """Creates announcement text, applies pregnancy injury, and returns involved cats."""
    text = choice(get_pregnancy_strings()[announcement_key])
    event_text = text
    severity = choices(["minor", "major"], [3, 1], k=1)[0]
    pregnant_cat.get_injured("pregnant", severity=severity)
    text += choice(get_pregnancy_strings()[f"{severity}_severity"])
    text = event_text_adjust(
        Cat,
        text,
        main_cat=pregnant_cat,
        random_cat=random_cat,
        clan=game.clan,
    )
    involved_cats = [pregnant_cat.ID]
    involved_cats = _append_second_parent_if_mentioned(
        involved_cats, event_text, mentioned_cat or random_cat
    )
    return text, involved_cats


def _append_second_parent_if_mentioned(
    involved_cats: List[str], event_text: str, mentioned_cat: Optional[Cat]
) -> List[str]:
    """
    Appends the second parent/mate ID only if the event text mentions r_c.
    :param involved_cats: the cats involved in the invent, usually the first and second parent

    :return: involved_cats dict with mentioned_cat included if needed
    """
    if mentioned_cat and "r_c" in event_text and mentioned_cat.ID not in involved_cats:
        involved_cats.append(mentioned_cat.ID)
    return involved_cats


def _set_affair_visibility(
    cat: Optional[Cat] = False,
    is_affair_known: Optional[bool] = False,
    pregnant_cat: Optional[Cat] = False,
):
    """Store whether an affair was explicitly announced in pregnancy data."""
    target_cat = cat or pregnant_cat
    if not target_cat or not game.clan:
        return
    pregnancy = game.clan.pregnancy_data.get(target_cat.ID)
    if pregnancy is None:
        return
    pregnancy["affair_known"] = is_affair_known
