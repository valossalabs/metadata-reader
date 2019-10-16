# -*- coding: utf-8 -*-
""" Various core-metadata related utilities.

"""
from __future__ import print_function, unicode_literals
from __future__ import absolute_import
from __future__ import division

import os
from io import open
import operator
import json

import logging
logger = logging.getLogger(__name__)
if __name__ == "__main__":
    raise NotImplementedError("Not designated to be run, please use import statement.")


class MetadataVersion:

    @staticmethod
    def categories(version):
        version_added = (1, 3, 3)
        if type(version) in [bytes, str]:
            version = [int(i) for i in version.split('.')]

        # If version_added > version: return False else return True
        # if version_added > version: return False
        if version_added[0] > version[0]: return False
        if version_added[1] > version[1]: return False
        if version_added[2] > version[2]: return False
        return True


class LengthSum(object):
    """Class to allow changing addition type.

    Union type addition simply extends time range when adding

    Normal type addition just adds end-start each time
    """
    UNION = "union"
    NORMAL = "normal"

    def __init__(self, sum_type=None):
        if sum_type is None:
            sum_type = LengthSum.NORMAL
        self.compress_flag = False
        if sum_type == LengthSum.UNION:
            self.add = self.add_union
            self.sum_type = LengthSum.UNION
            self.intervals = []
            self.id_dict = {}
        elif sum_type == LengthSum.NORMAL:
            self.add = self.add_normal
            self.sum_type = LengthSum.NORMAL
            self.sum = 0.0
        else:
            raise TypeError("sum_type must be either LengthSum.UNION or LengthSum.NORMAL")

    def __str__(self):
        return str(self.__float__())

    def __repr__(self):
        return repr(self.__float__())

    def __float__(self):
        self.compress()
        if self.sum_type == LengthSum.UNION:
            if len(self.id_dict) > 0:
                r_sum = sum([i[1]-i[0] for inters in self.id_dict.values() for i in inters])
            else:
                r_sum = sum([i[1]-i[0] for i in self.intervals])
            return float(r_sum)
        return self.sum

    def __truediv__(self, other):
        return self.__float__() / other

    def __add__(self, other):
        self.add(other)
        return self

    # Comparing sums:
    def __gt__(self, other):
        return self.__float__() > other.__float__()

    def __lt__(self, other):
        return self.__float__() < other.__float__()

    def duration_between(self, start=None, end=None):

        def sum_func(_item):
            _ret_sum = 0.0
            for ss, se in _item:
                count_from = ss if start is None or ss >= start else start
                count_to = se if end is None or se <= end else end
                if count_from < count_to:
                    _ret_sum += count_to - count_from
            return _ret_sum

        self.compress()
        if len(self.id_dict) > 0:
            ret_sum = 0.0
            for item in self.id_dict.values():
                ret_sum += sum_func(item)
        else:
            ret_sum = sum_func(self.intervals)
        return ret_sum

    def add_union(self, ss, se=None, id=None):
        # If trying to add self, do nothing:
        if id is not None:
            if id not in self.id_dict:
                self.id_dict[id] = []  # new interval list
            target = self.id_dict[id]
        else:
            target = self.intervals
        if ss is self:
            pass
        elif se is None and type(ss) == LengthSum:
            for interval in ss.intervals:
                target.append(interval)
        else:
            target.append((ss, se))
        self.compress_flag = True

    def add_normal(self, ss, se=None, id=None):
        if se is None and type(ss) == LengthSum:
            self.sum += ss.sum
        else:
            self.sum += se - ss

    def compress(self):
        if self.compress_flag:
            if self.sum_type == LengthSum.UNION and len(self.id_dict) > 0:
                for k in self.id_dict.keys():
                    self.id_dict[k] = self._compress(self.id_dict[k])
            else:
                self.intervals = self._compress(self.intervals)
            self.compress_flag = False

    @staticmethod
    def _compress(source_list):
        if not source_list:
            return source_list
        source_list.sort(key=lambda lis: lis[0])
        return_list = [source_list[0]]
        for cell in source_list[1:]:
            if cell[0] > return_list[-1][1]:
                return_list.append(cell)
            elif return_list[-1][1] <= cell[1]:
                return_list[-1] = (return_list[-1][0], cell[1])
        return return_list


def load_json(json_path):
    """Simply open json-file and return contents"""
    with open(json_path, 'r', encoding="utf-8") as f:
        j = json.load(f)
    return j


def detection_length(detection):
    """Calculates total duration of detection based on it's occurrences."""
    ret_val = 0.0
    for occ in detection.get("occs",[]):
        ret_val += occ["se"]-occ["ss"]
    return ret_val


class CoreMetadata:

    def __init__(self, metadata, blacklist=None):
        self.metadata = metadata
        self._blacklist = blacklist

        self._categories = None
        self._emotions = None
        self._available_emotions = None
        self._occurrences = None
        self._occurrences_valence = None

    @property
    def media_length(self):
        """
        Duration of analysed video in seconds.
        """
        return self.metadata["media_info"]["technical"]["duration_s"]

    @property
    def media_title(self):
        """Media info, from customer, title

        :return: Video title given by customer.
        """
        return self.metadata["media_info"]["from_customer"]["title"]

    @property
    def available_emotions(self):
        """All emotions found in core metadata"""
        self._gen_emotions()
        return self._available_emotions

    def detections(self, detection_types=None, categories=None, sort_by=None, n_per_type=None):
        """Yields detection_id, detection pairs.

        :param detection_types: List only items from these detection types.
        :param categories: List only items that has these category tags.
        :param sort_by: choices: ["detection_id", "prominence"]
        :param n_per_type: Maximum amount of yielded items per detection_type.
        :return:
        """

        if detection_types is None:
            detection_types = self.metadata["detection_groupings"]["by_detection_type"]
        else:
            if isinstance(detection_types, str):
                detection_types = [detection_types, ]

        if sort_by == "prominence":
            for detection_type in detection_types:
                if detection_type not in self.metadata["detection_groupings"]["by_detection_type"]:
                    logger.debug("Detection type \"{}\" not found, skipping.".format(detection_type))
                    continue
                count = 0
                for detection_id in self.metadata["detection_groupings"]["by_detection_type"][detection_type]:
                    detection = self.metadata["detections"][detection_id]

                    # Filtering:
                    if self.blacklisted(detection=detection):
                        continue
                    if categories is not None and not set(self.categories(detection=detection)) & set(categories):
                        continue
                    if n_per_type is not None and count >= n_per_type:
                        break

                    yield detection_id, self.metadata["detections"][detection_id]
                    count += 1

        elif sort_by in ("detection_id", None):
            count = {}
            for detection_id in sorted(self.metadata["detections"], key=int):

                # Filtering
                if self.blacklisted(detection_id=detection_id):
                    continue
                if categories is not None and not set(self.categories(detection_id=detection_id)) & set(categories):
                    continue
                detection_type = self.metadata["detections"][detection_id]["t"]
                if detection_type not in detection_types:
                    continue
                if detection_type in count:
                    if n_per_type is not None and count[detection_type] >= n_per_type:
                        break
                else:
                    count[detection_type] = 0

                yield detection_id, self.metadata["detections"][detection_id]
                count[detection_type] += 1
        else:
            raise ValueError("Invalid sort_by-value: %s" % str(sort_by))

    def occurrences(self, detection_types=None, categories=None, sort_by=None, start_second=None, end_second=None,
                    extras=None):
        """Yields all occurrences sorted by start time of occurrence.

        :param detection_types:
        :param categories:
        :param sort_by: choices: "start_second", "valence"
        :param start_second: Yield only occurrences that end after this.
        :param end_second: Yield only occurrences that start before this.
        :param extras: set of extra information needed in occurrence data.
        :return:
        """
        if extras:
            extras = set(extras)
        else:
            extras = set()
        if sort_by == "valence":
            extras.add("valence")
        self._gen_occurrences(detection_types=detection_types, categories=categories, extras=extras,
                              start_second=start_second, end_second=end_second)
        if sort_by is None:  # Default, by detection id
            iterable = sorted(
                self._occurrences,
                key=lambda d: int(d["d"]),
            )
        elif sort_by == "start_second":
            iterable = sorted(
                self._occurrences,
                key=operator.itemgetter("ss"),
            )

        elif sort_by == "valence":
            iterable = sorted(
                filter(  # Removes items with "val" value None
                    lambda d: d["val"] is not None,
                    # operator.itemgetter("val"), Would remove 0.000 too...
                    self._occurrences,
                ),
                key=operator.itemgetter("val"),
                reverse=True,
            )

        elif sort_by == "duration":
            iterable = sorted(
                self._occurrences,
                key=lambda d: float(d["se"]) - float(d["ss"]),
                reverse=True,
            )
        else:
            raise ValueError("sort_by argument does not accept '%s' as value" % sort_by)
        for occ in iterable:
            yield occ

    def _gen_occurrences(self, detection_types=None, categories=None, start_second=None, end_second=None, extras=None):
        if self._occurrences is not None:
            return
        self._occurrences = []
        for det_id, detection in self.detections(detection_types=detection_types):
            if categories is not None:
                if ("categ" not in detection
                        or "tags" not in detection["categ"]
                        or not set(categories) & set(detection["categ"]["tags"])):
                    continue

            if self.blacklisted(detection=detection):
                continue

            if "occs" in detection:
                for occ in detection["occs"]:
                    if start_second is not None and occ["se"] < start_second:
                        # Occurrence ended before start_second
                        continue
                    if end_second is not None and occ["ss"] > end_second:
                        # Occurrence started after end_second
                        continue
                    d = {key: value for key, value in occ.items()}
                    d["d"] = det_id
                    d["t"] = detection["t"]

                    if extras and "valence" in extras:
                        if detection["t"] != "human.face":
                            d["val"] = None
                        else:
                            # Add "val" key to occ-dict, containing average valence value over occurrence.
                            ss = int(occ["ss"])
                            se = int(occ["se"])+1
                            val_list = [0, 0]  # len, sum (for calculating average)
                            for index, secdata in self.second_data(start_second=ss, end_second=se):
                                for data in secdata:
                                    if data["d"] == det_id:
                                        if "a" not in data or "sen" not in data["a"] or "val" not in data["a"]["sen"]:
                                            continue
                                        val_list[0] += 1
                                        val_list[1] += data["a"]["sen"]["val"]
                            d["val"] = round(val_list[1] / val_list[0], 3) if val_list[0] != 0 else None

                    if extras and "similar_to" in extras and detection["t"] == "human.face":
                        # Add "name" and "recognition confidence" keys to occ-dict.
                        if "a" in detection and "similar_to" in detection["a"]:
                            d["name"] = detection["a"]["similar_to"][0]["name"]
                            d["recog_c"] = detection["a"]["similar_to"][0]["c"]
                    self._occurrences.append(d)

    def second_data(self, start_second=0, end_second=None):
        """Yields second, data pairs."""
        for second, data in enumerate(
                self.metadata["detection_groupings"]["by_second"][start_second:end_second],
                start=start_second):
            yield second, [x for x in data if not self.blacklisted(detection_id=x["d"])]

    def label(self, detection_id=None, face_name=False):
        """Returns label of detection. For faces returns similar_to value instead."""
        if detection_id is not None:
            label = self.metadata["detections"][detection_id]["label"]
            if face_name and label == "face":
                return self._similar_to_name(detection_id)
            if face_name and label == "face group":
                return self._similar_to_name(detection_id)
            else:
                return label

    def blacklisted(self, detection=None, detection_id=None):
        """Checks if the detection has been blacklisted in blacklist.json

        :param detection: Regular detection-dict.
        :param detection_id:
        :return: True if blacklisted, False otherwise.
        """
        if self._blacklist is None:
            return False
        if detection_id is not None:
            detection = self.metadata["detections"][detection_id]
        categ = set(self.categories(detection=detection))
        strong_bl = set(self._blacklist["category_tags_strong_blacklist"])
        weak_bl = set(self._blacklist["category_tags_weak_blacklist"]) | strong_bl
        if detection is not None:
            if (
                    "label" in detection and detection["label"] in self._blacklist["concept_tags"]
                    or categ and ((categ & strong_bl) or (not categ - weak_bl))
            ):
                return True
        return False

    def detection_type(self, detection_id=None):
        """Returns detection type"""
        if detection_id is not None:
            return self.metadata["detections"][detection_id]["t"]

    def detection_types(self):
        """Goes through all detection types in metadata"""
        for detection_type, detection_ids in self.metadata["detection_groupings"]["by_detection_type"].items():

            yield detection_type, [det_id for det_id in detection_ids if not self.blacklisted(detection_id=det_id)]

    def emotion(self, detection_id):
        """Return durations for each emotion"""
        self._gen_emotions()
        val_sum = 0
        val_counter = 0
        emos = dict()
        for sen in self._emotions.get(detection_id, []):
            if "val" in sen:
                val_sum += sen["val"]
                val_counter += 1
            if "emo" in sen:
                for emo in sen["emo"]:
                    if emo["e"] not in emos:
                        emos[emo["e"]] = {
                            "sum": 0,
                            "count": 0,
                        }
                    emos[emo["e"]]["sum"] += emo["c"]
                    emos[emo["e"]]["count"] += 1
        return {e: emos[e]["count"] if e in emos else 0
                for e in self._available_emotions}

    def _gen_emotions(self):
        """Populate self._emotions with emotions and
        self._available_emotions with all emotions in the
        metadata file
        Formats:
            self._emotions[detection_id] = [
                {'emo':list, 'val':float}
            ]
            self._available_emotions = {"emotion1", "emotion2"...}
        """
        if self._emotions is None:
            self._emotions = {}
            self._available_emotions = set()

            for second, secdata in self.second_data():
                for detdata in secdata:
                    if "a" not in detdata or "sen" not in detdata["a"]:
                        # Skip if no sentiment data available
                        continue
                    if detdata["d"] not in self._emotions:
                        self._emotions[detdata["d"]] = []
                        if "emo" in detdata["a"]["sen"]:
                            for e in detdata["a"]["sen"]["emo"]:
                                self._available_emotions.add(e["e"])
                    self._emotions[detdata["d"]].append(
                        detdata["a"]["sen"]
                    )

    def categories(self, detection_types=None, with_category=None, start_second=0, end_second=None, detection_id=None,
                   detection=None):
        """Generator which yields all categories and their durations on default.

        :param detection_types: Category tags in selected detection types
        :param with_category: Ignore category tags that are not in `with_category` list/set/tuple...
        :param start_second: Yield only categories that are present after this time.
        :param end_second: Yield only categories that are present before this time.
        :param detection_id: Yield categories listed for this detection
        :param detection: Yield categories listed for this detection
        :return: Yields detection_type, category tag and duration between start_second and end_second.
        :rtype: Generator(tuple)
        """
        if detection_id is not None:
            detection = self.metadata["detections"][detection_id]
        if detection is not None:
            if "categ" in detection and "tags" in detection["categ"]:
                for tag in detection["categ"]["tags"]:
                    yield tag
        else:
            self._gen_categories(with_category, start_second=start_second, end_second=end_second)
            for det_type in self._categories:
                if detection_types is None or \
                        det_type in detection_types:
                    for tag, _ in sorted(self._categories[det_type].items(),
                                         key=lambda x: x[1]["duration"].duration_between(start=start_second,
                                                                                         end=end_second),
                                         reverse=True):
                        duration = self._categories[det_type][tag]["duration"].duration_between(start=start_second,
                                                                                                end=end_second)
                        if duration == 0.0:
                            continue
                        yield det_type, tag, duration

    def _gen_categories(self, with_category=None, start_second=0, end_second=None):
        """Populate self._categories with useful data
        Format:
            self._categories[detection_type][tag] = {
                "detections": [detections],
                "duration": LengthSum("union")
            }


        :param with_category: set of categories to include or None for all categories.
        :param start_second: Categories present after this.
        :param end_second: Categories present before this.
        :return: None
        """
        if self._categories is None:
            self._categories = dict()

            for det_type, det_ids in self.detection_types():
                if det_type not in self._categories:
                    self._categories[det_type] = dict()
                for det_id in det_ids:
                    detection = self.metadata["detections"][det_id]
                    if self.blacklisted(detection=detection):
                        continue

                    if "categ" in detection and "tags" in detection["categ"] and \
                            (with_category is None or
                             set(with_category) & set(detection["categ"]["tags"])):
                        for tag in detection["categ"]["tags"]:
                            if tag not in self._categories[det_type]:
                                self._categories[det_type][tag] = {
                                    "detections": [],
                                    "duration": LengthSum("union"),
                                }
                            self._categories[det_type][tag]["detections"].append(detection)
                            for occ in detection.get("occs", []):
                                self._categories[det_type][tag]["duration"].add(occ["ss"], occ["se"])

    def _similar_to_name(self, detection_id, name_only=False):
        """Tries hard to match detection id into person name."""
        if self.type_by_id(detection_id) == "human.face_group":

            if "a" in self.metadata["detections"][detection_id] \
                        and "face_det_ids" in self.metadata["detections"][detection_id]["a"]:
                ids = self.metadata["detections"][detection_id]["a"]["face_det_ids"]
                names = [self._similar_to_name(id, name_only=True) for id in ids]
                return "Face_group: " + ", ".join(names)
            else:
                return "Face_group (id: {})".format(detection_id)
        else:

            if "a" in self.metadata["detections"][detection_id] \
                        and "similar_to" in self.metadata["detections"][detection_id]["a"]:
                return self.metadata["detections"][detection_id]["a"]["similar_to"][0]["name"]
            else:
                return detection_id if name_only else "Face (id: {})".format(detection_id)

    # Deprecated methods:

    def label_by_id(self, detection_id):
        """Returns detection label"""
        # Deprecated as of 29.1.2019
        from warnings import warn
        warn("`label_by_id` is deprecated, use `label` instead.", DeprecationWarning)
        return self.metadata["detections"][detection_id]["label"]

    def type_by_id(self, detection_id):
        """Returns detection type"""
        # Deprecated as of 29.1.2019
        from warnings import warn
        warn("`type_by_id` is deprecated, use `detection_type` instead.", DeprecationWarning)
        return self.metadata["detections"][detection_id]["t"]

    def detections_by_detection_type(self, detection_type=None):
        # Deprecated as of 15.1.2019
        from warnings import warn
        warn("`detections_by_detection_type` is deprecated, use `detections` instead.", DeprecationWarning)
        for detection_id in self.metadata["detection_groupings"]["by_detection_type"].get(detection_type, []):
            yield detection_id, self.metadata["detections"][detection_id]

    def _detections_by_detection_type(self, detection_type=None):
        for detection_id in self.metadata["detection_groupings"]["by_detection_type"][detection_type]:
            yield detection_id
