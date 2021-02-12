# -*- coding: utf-8 -*-
"""Metadata-reader

This module contains all functions, classes etc. to read Valossa Core metadata.
"""
from __future__ import print_function, unicode_literals
from __future__ import absolute_import
from __future__ import division

from decimal import Decimal  # Division by 20 causes rounding behaviour, which isn't pretty.
from collections import OrderedDict

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from .lib.mdutil import CoreMetadata, LengthSum


class AppError(Exception):
    """Custom error to catch so that we don't catch some other error by mistake."""


class MetadataReader(object):
    """Contains various methods for core_metadata parsing."""

    def __init__(self, core_metadata, blacklist=None):
        """Each instance is about a specific core_metadata.

        :param dict core_metadata: Loaded core_metadata.
        """
        # blacklist isn't actually being used yet.
        self.metadata = core_metadata
        self.core_metadata = CoreMetadata(self.metadata, blacklist=blacklist)

    def list_detections(self, **kwargs):
        """Generator which yields OrderedDict for each detection.

        OrderedDict keys:
        * detection ID
        * detection type
        * label
        * Valossa concept ID
        * GKG concept ID
        * more information


        :param kwargs: Keyword arguments are just passed forward here. Those are
                       mainly used for filtering unwanted detections out.
        :return: Generator which yields one row at time.
        :rtype: Generator[collections.OrderedDict]
        """
        extras = set()
        if kwargs["detection_persons"] is not None:
            extras.add("similar_to")
        if kwargs["extra_header"] is not None:
            extras |= set(kwargs["extra_header"])
        for det_id, detection in self.core_metadata.detections(
            n_per_type=kwargs["n_most_prominent_detections_per_type"],
            categories=kwargs["category"],
            detection_types=kwargs["detection_types"],
            sort_by=kwargs["sort_by"],
        ):
            # Limit listing:
            if not _conditions_match(detection, **kwargs):
                continue
            vco_id = ""
            if "cid" in detection:
                vco_id = detection["cid"]
            gkg_id = ""
            if "ext_refs" in detection and "gkg" in detection["ext_refs"]:
                gkg_id = detection["ext_refs"]["gkg"]["id"]

            # more_info = _detection_type_specific_information(detection)
            d = OrderedDict([
                ("detection ID",       det_id),
                ("detection type",       detection["t"]),
                ("label",              detection["label"]),
                ("Valossa concept ID", vco_id),
                ("GKG concept ID",     gkg_id),
                # ("more information",   more_info),
            ])
            if "similar_to" in extras:
                d["similar to"] = _person_name(detection=detection) if detection["t"] == "human.face" else ""
            if "gender" in extras:
                d["gender"] = _person_gender(detection=detection) if detection["t"] == "human.face" else ""
            if "text" in extras:
                d["text"] = _textregion_text(detection=detection) if "visual.text_region" in detection["t"] else ""
            yield d

    def list_detections_by_second(self, **kwargs):
        """Generator which yields detections for each second as OrderedDict.

        Output headers (default):

        * second
        * timestamp
        * detection ID
        * detection type
        * confidence
        * label
        * Valossa concept ID
        * GKG concept ID
        * more information

        Output headers (short):

        * timestamp
        * label
        * label
        ...

        Output headers (srt):

        * start
        * stop
        * line of labels


        :param kwargs: Keyword arguments used here:
            - 'output_format' (str). If 'srt, use self.list_subtitle() -generator.
            - 'short' (bool). If True, use self.list_short() -generator.
            - 'valence' (bool). If True, use self.list_sentiment() -generator.
            - 'min_confidence' (float). Valossa Core metadata has confidence values between 0.5 and 1.0 so we encourage
              to use values between those in this argument, or None.
        :return: Generator which yields one row at time.
        :rtype: Generator[collections.OrderedDict]
        """
        extras = set()
        if kwargs["detection_persons"] is not None:
            extras.add("similar_to")
        if kwargs["extra_header"] is not None:
            extras |= set(kwargs["extra_header"])

        if kwargs.get("output_format") == "srt":
            # Output subtitles
            for item in self.list_subtitle(**kwargs):
                yield item
        elif kwargs.get("short", False):
            # Shorter form
            for item in self.list_short(**kwargs):
                yield item
        elif kwargs.get("sentiment", False):
            # Sentiment (not emotions)
            for item in self.list_sentiment(**kwargs):
                yield item
        else:
            # Default procedure
            for sec_index, detdata in self._detections_by_second(**kwargs):
                detection_id = detdata["d"]
                detection = self.metadata["detections"][detection_id]
                vco_id = detection.get("cid", "")
                if "ext_refs" in detection and "gkg" in detection["ext_refs"]:
                    gkg_id = detection["ext_refs"]["gkg"]["id"]
                else:
                    gkg_id = ""

                confidence = ""
                if "c" in detdata:
                    # TESTING FOR ARGS.MIN_CONFIDENCE
                    if kwargs.get("min_confidence", None) and detdata["c"] < kwargs.get("min_confidence"):
                        continue
                    confidence = detdata["c"]

                # more_info = _detection_type_specific_information(detection)
                d = OrderedDict([
                    ("second",             sec_index),
                    ("timestamp",          _seconds_to_timestamp_hhmmss(sec_index)),
                    ("detection ID",       detection_id),
                    ("detection type",     detection["t"]),
                    ("confidence",         confidence),
                    ("label",              detection["label"]),
                    ("Valossa concept ID", vco_id),
                    ("GKG concept ID",     gkg_id),
                    # ("more information",   more_info),
                ])
                if "valence" in extras:
                    d["valence from -1.0 to 1.0"] = detdata["a"]["sen"]["val"] \
                        if "a" in detdata and "sen" in detdata["a"] and "val" in detdata["a"]["sen"] else ""
                if "similar_to" in extras:
                    d["similar to"] = _person_name(detection=detection) if detection["t"] == "human.face" else ""
                if "gender" in extras:
                    d["gender"] = _person_gender(detection=detection) if detection["t"] == "human.face" else ""
                if "text" in extras:
                    d["text"] = _textregion_text(detection=detection) if "visual.text_region" in detection["t"] else ""
                yield d

    def list_sentiment(self, **kwargs):
        """Generator which yields sentiment data by second from metadata.

        Output headers:

        second,
        timestamp,
        speech valence,
        face valence (1),
        face valence (2),
        ...


        :param kwargs: Arguments used here:
            - 'start_second' (int). In order to have correct index.
        :return: Generator which yields one row at time.
        :rtype: Generator[collections.OrderedDict]
        """
        # First pass: add all persons to list.
        sentiment_person_ids = []
        for index, data in self._detections_by_second(**kwargs):
            if "a" in data and "sen" in data["a"]:
                if data["d"] not in sentiment_person_ids:
                    sentiment_person_ids.append(data["d"])

        # Sort persons at prominence order:
        sentiment_person_ids.sort(
            key=lambda x: self.metadata["detection_groupings"]["by_detection_type"]["human.face"].index(x))
        speech_sentiment = False
        for detection_id, detection in self.metadata["detections"].items():
            if "a" in detection and "sen" in detection["a"]:
                speech_sentiment = True
                break
        if not (speech_sentiment or sentiment_person_ids):
            raise AppError("No sentiment data found on metadata")

        sec_index = kwargs.get("start_second", 0)
        for second_data in self._get_secdata_interval(**kwargs):
            yield_bool = False
            line_dict = OrderedDict([
                ("second", sec_index),
                ("timestamp", _seconds_to_timestamp_hhmmss(sec_index)),
            ])
            if speech_sentiment:
                line_dict["speech valence"] = ""
            line_dict.update([("face valence (%s)" % key, "") for key in sentiment_person_ids])
            for occ in second_data:
                if occ["d"] in sentiment_person_ids:
                    if "a" in occ and "sen" in occ["a"] and "val" in occ["a"]["sen"]:
                        line_dict["face valence (%s)" % occ["d"]] = occ["a"]["sen"]["val"]
                        yield_bool = True
                elif speech_sentiment and self.metadata["detections"][occ["d"]]["t"] == "audio.speech":
                    detection = self.metadata["detections"][occ["d"]]
                    if "a" in detection and "sen" in detection["a"] and "val" in detection["a"]["sen"]:
                        line_dict["speech valence"] = detection["a"]["sen"]["val"]
                        yield_bool = True

            sec_index += 1
            if yield_bool:
                yield line_dict

    def list_short(self, **kwargs):
        """Special case of list-detections-by-second.

        :param kwargs: Arguments used here:
            - 'detection_label' (string).
        :return: Yields only timestamp and labels.
        :rtype: Generator[collections.OrderedDict]
        """
        for second in self._get_labels_by_second(**kwargs):
            if len(second) > 1:
                if kwargs.get("detection_label", None) and not _label_match(second[1:], kwargs.get("detection_label")):
                    continue
                yield OrderedDict([
                    ("timestamp", _seconds_to_timestamp_hhmmss(second[0])),
                    ("labels", second[1:]),
                ])

    def list_categories(self, **kwargs):
        """List all categories found in metadata

        :param kwargs:
        :return: Yield each category and it's duration in seconds.
        :rtype: Generator[collections.OrderedDict]
        """
        det_types = kwargs.get("detection_types").split(",") if kwargs.get("detection_types") is not None else None
        # yield ["detection type", "category", "duration"]
        counter = 0
        for det_type, tag, duration in self.core_metadata.categories(
                detection_types=det_types,
                with_category=kwargs.get("category"),
                start_second=kwargs["start_second"],
                end_second=kwargs["end_second"],
        ):
            counter += 1
            if kwargs.get("n_most_longest") is not None and counter > kwargs["n_most_longest"]:
                break
            # yield det_type, tag, "{:.3f}".format(float(data["duration"]))

            yield OrderedDict([
                ("detection type", det_type),
                ("category tag", tag),
                ("duration_s", "{:.3f}".format(duration)),
            ])

    def list_occurrences(self, **kwargs):
        """Generator which yields information about each occurrence as OrderedDict.

        :param kwargs:
        :return: Dictionary containing relevant data.
        :rtype: Generator[collections.OrderedDict]
        """
        extras = set()
        if kwargs["detection_persons"]:
            extras.add("similar_to")
        if kwargs["extra_header"]:
            extras |= set(kwargs["extra_header"])
        for occ in self.core_metadata.occurrences(extras=extras,
                                                  sort_by=kwargs["sort_by"],
                                                  detection_types=kwargs["detection_types"],
                                                  categories=kwargs["category"],
                                                  start_second=kwargs["start_second"],
                                                  end_second=kwargs["end_second"],
                                                  ):
            if not _conditions_match(self.metadata["detections"][occ["d"]], **kwargs):
                continue
            confidence = str(occ["c_max"]) if "c_max" in occ else ""
            d = OrderedDict([
                ("detection ID", occ["d"]),
                ("detection type", occ["t"]),
                ("label", self.core_metadata.label(detection_id=occ["d"])),
                ("start second", occ["ss"]),
                ("end second", occ["se"]),
                ("shot index", occ["shs"]),
                ("confidence", confidence),
                ("category tags", " ".join(self.core_metadata.categories(detection_id=occ["d"]))),
            ])
            if "valence" in extras:
                d["valence from -1.0 to 1.0"] = occ["val"] if occ["val"] is not None else "-"
            if "similar_to" in extras:
                if "name" in occ:
                    d["similar to"] = occ["name"]
                    d["face_recognition_confidence"] = occ["recog_c"]
                else:
                    d["similar_to"] = _person_name(
                        self.metadata["detections"][occ["d"]], occ["d"])
                    d["face_recognition_confidence"] = ""
            if "text" in extras:
                detection = self.metadata["detections"][occ["d"]]
                d["text"] = _textregion_text(detection=detection) if "visual.text_region" in detection["t"] else ""
            yield d

    def list_subtitle(self, delta=0.5, min_sub_interval=2, **kwargs):
        """Generate subtitles out of detected labels.
        Subtitle does not allow limiters at this time.

        :param delta: The higher the delta, the later the subtitles show up compared to occurrence.
        :param min_sub_interval: Minimum time to show each subtitle.
        :param kwargs: Arguments used here:
            - 'start_second' (int).
            - 'end_second' (int).
            - 'detection_types' (string).
        :return: Yields subtitles one field at time.
        :rtype: Generator[collections.OrderedDict]
        """
        def min_max(list_par, n):
            """Returns min and max"""
            min_n = max_n = list_par[0][n]
            for s in list_par[1:]:
                if s[n] > max_n:
                    max_n = s[n]
                elif s[n] < min_n:
                    min_n = s[n]
            return min_n, max_n

        space = 0.05
        sub_data_gen = self.core_metadata.occurrences(
            start_second=kwargs.get("start_second"),
            end_second=kwargs.get("end_second"),
            detection_types=kwargs.get("detection_types"),
            sort_by="start_second",
        )
        if kwargs.get("detection_types") == "audio.speech":
            # Assume that this can be outputted as it is.
            for start, stop, label in sub_data_gen:
                yield [start, stop, label]
            return

        last_end_time = -space
        subtitle_labels = []
        for occ in sub_data_gen:
            start = occ["ss"]
            stop = occ["se"]
            label = self.core_metadata.label(detection_id=occ["d"])
            if [start, stop, label] not in subtitle_labels:
                subtitle_labels.append([start, stop, label])
            s_min, s_max = min_max(subtitle_labels, 0)
            while last_end_time + 4 * min_sub_interval < s_max:
                # Start time
                start_time = max(last_end_time + space, s_min + delta)

                # Add labels to subtitle line
                line_labels = []
                for [line_start, line_stop, line_label] in subtitle_labels:
                    if line_start < start_time - delta + min_sub_interval:
                        line_labels.append(line_label)

                # End time
                end_time_1 = start_time + min_sub_interval
                end_time_2 = min([s[1] for s in subtitle_labels])
                try:
                    end_time_3 = min(
                        [s[0] for s in subtitle_labels if s[0] > start_time - delta + min_sub_interval])
                except ValueError:
                    # In case subtitle_labels are exhausted:
                    end_time_3 = float('inf')
                end_time = max(min(end_time_2, end_time_3), end_time_1)

                # YIELD (Print)
                yield OrderedDict([
                    ("start_time", start_time),
                    ("end_time", end_time),
                    ("labels", line_labels),
                ])
                # self.writer.writerow([start_time, end_time] + line_labels)

                # Remove old labels:
                last_end_time = end_time
                subtitle_labels = [x for x in subtitle_labels if x[1] >= end_time - delta]
                if not subtitle_labels:
                    break
                s_min, s_max = min_max(subtitle_labels, 0)

        # Handle remaining subtitle labels:
        while subtitle_labels:
            # Start time
            start_time = max(last_end_time + space, s_min + delta)

            # Add labels to subtitle line
            line_labels = []
            for [line_start, line_stop, line_label] in subtitle_labels:
                if line_start < start_time - delta + min_sub_interval:
                    line_labels.append(line_label)

            # End time
            end_time_1 = start_time + min_sub_interval
            end_time_2 = min([s[1] for s in subtitle_labels])
            try:
                end_time_3 = min(
                    [s[0] for s in subtitle_labels if s[0] > start_time - delta + min_sub_interval])
            except ValueError:
                # In case subtitle_labels are exhausted:
                end_time_3 = float('inf')
            end_time = max(min(end_time_2, end_time_3), end_time_1)

            # (Print) YIELD
            yield OrderedDict([
                ("start_time", start_time),
                ("end_time", end_time),
                ("labels", line_labels),
            ])

            # Remove old labels:
            last_end_time = end_time
            subtitle_labels = [x for x in subtitle_labels if x[1] >= end_time - delta]
            if not subtitle_labels:
                break
            s_min, s_max = min_max(subtitle_labels, 0)

    def list_summary(self, detection_type=None, **kwargs):  # TODO: perhaps redesign this.
        """Method to gather list containing summary.

        :param detection_type: Chosen detection type for summary. Default: human.face + visual.context.
        :type detection_type: str or None
        :param kwargs: Arguments used here:
            - 'addition_method' (string). Choose 'union' or 'normal', default is 'union'
            - 'min_confidence' (float).
            - 'skip_unknown_faces' (bool).
            - 'separate_face_identities' (bool).
            - 'n_most_prominent_detections_per_type' (int).
        :return: {detection_type: [
                    name_or_label,
                    screentime,
                    (confidence,)
                    of_video_length
                  ]}
        :rtype: Generator[dict[str, collections.OrderedDict]]
        """
        if detection_type is None:
            for partial_dict in self.list_summary(detection_type="human.face", **kwargs):
                yield partial_dict
            for partial_dict in self.list_summary(detection_type="visual.context", **kwargs):
                yield partial_dict
            return

        if '*' in detection_type:
            for d_type in self.metadata["detection_groupings"]["by_detection_type"]:
                if _types_match(d_type, detection_type) and 'iab' not in d_type:
                    for partial_dict in self.list_summary(detection_type=d_type, **kwargs):
                        yield partial_dict
            return

        video_length = self.metadata["media_info"]["technical"]["duration_s"]

        add_type = kwargs.get("addition_method", "union")
        summ_dict = {detection_type: {}}
        summ_list = {detection_type: []}
        if detection_type == "human.face":
            if "human.face" in self.metadata["detection_groupings"]["by_detection_type"]:
                for detection_id in self.metadata["detection_groupings"]["by_detection_type"][detection_type]:

                    detection = self.metadata["detections"][detection_id]

                    if "similar_to" in detection["a"]:
                        # Take first cell, as it should be most accurate:
                        name = detection["a"]["similar_to"][0]["name"]
                        confidence = detection["a"]["similar_to"][0]["c"]
                        if kwargs.get("min_confidence") and \
                                detection["a"]["similar_to"][0]["c"] < kwargs.get("min_confidence"):
                            continue
                    else:
                        # UNKNOWN PERSON
                        if kwargs.get("skip_unknown_faces", None):
                            continue
                        name = _person_name(detection, detection_id)
                        confidence = "-"

                    screentime = LengthSum(add_type)
                    for occ in detection["occs"]:
                        # human.face doesn't have occ confidence
                        screentime.add(occ["ss"], occ["se"])
                    summ_dict[detection_type][detection_id] = OrderedDict([
                        ("name", name),
                        ("face_recognition_confidence", confidence),
                        ("screentime_s", screentime),
                        # ("of_video_lenght", float(screentime)/video_length),
                    ])
                    if kwargs.get("emotion"):
                        emotions = self.core_metadata.emotion(detection_id)
                        summ_dict[detection_type][detection_id].update(sorted(emotions.items()))

                #
                # Combine identities:
                if not kwargs.get("separate_face_identities", False):
                    face_dict = {}
                    for id, item in summ_dict[detection_type].items():
                        if item["name"] in face_dict:
                            # Add screentime and emotions and use smaller confidence.
                            face_dict[item["name"]]["screentime_s"].add(item["screentime_s"])
                            face_dict[item["name"]]["face_recognition_confidence"] = min(
                                    face_dict[item["name"]]["face_recognition_confidence"],
                                    item["face_recognition_confidence"])
                            if kwargs.get("emotion"):
                                for emotion in self.core_metadata.available_emotions:
                                    face_dict[item["name"]][emotion] += item[emotion]
                        else:
                            face_dict[item["name"]] = item

                    summ_list[detection_type] = face_dict.values()
        else:  # detection_type != "human.face"
            if detection_type in self.metadata["detection_groupings"]["by_detection_type"]:
                for detection_id in self.metadata["detection_groupings"]["by_detection_type"][detection_type]:
                    detection = self.metadata["detections"][detection_id]

                    # If categor(y|ies) given, allow only those
                    if kwargs.get("category"):
                        if "categ" in detection and "tags" in detection["categ"] and \
                                set(detection["categ"]["tags"]) & set(kwargs.get("category", [])):
                            # Detection has correct category!
                            pass
                        else:
                            # Either detection doesn't have categories at all, or just
                            # missing correct one: skip.
                            continue
                    # Testing for detection confidence
                    if kwargs.get("min_confidence") and not _min_confidence_match(detection, kwargs.get("min_confidence")):
                        continue
                    screentime = LengthSum(add_type)
                    for occ in detection["occs"]:
                        # Testing for occurrence confidence
                        if kwargs.get("min_confidence") and occ["c_max"] < kwargs.get("min_confidence"):
                            continue
                        screentime.add(occ["ss"], occ["se"])

                    summ_dict[detection_type][detection_id] = OrderedDict([
                        ("label", detection["label"]),
                        ("screentime_s", screentime),
                    ])
                summ_list[detection_type] = summ_dict[detection_type].values()

        # Sort and limit by n-most-prominent-detections-per-type
        n_first = kwargs.get("n_most_prominent_detections_per_type", None)
        yield {
            "summary": {
                detection_type: sorted(summ_list[detection_type],
                                       key=lambda v: float(v["screentime_s"]),
                                       reverse=True)[:n_first]
            }
        }

    def metadata_info(self):
        """Prints info about given metadata-file into sys.stdout

        Currently outputs:
            - metadata format
            - backend version
            - media title
            - video duration
            - description
            - video url

        :return: Does not return anything
        :rtype: None
        """

        versions = self.metadata["version_info"]
        media_info = self.metadata["media_info"]
        job_info = self.metadata["job_info"]["request"]["media"]

        print_list = [
            "Metadata format:  {}".format(versions["metadata_format"]),
            "Backend version:  {}".format(versions["backend"]),
            "",

            # MEDIA_INFO
            "Media title:      {}".format(media_info["from_customer"]["title"]),
            "Duration:         {}".format(_seconds_to_timestamp_hhmmss(media_info["technical"]["duration_s"])),
            "Description:      {}".format("" if job_info["description"] is None else job_info["description"]),
            "",
        ]

        if job_info["video"]["url"] is not None:
            print_list.append("Video URL:        {}".format(job_info["video"]["url"]))
        if job_info["transcript"]["url"] is not None:
            print_list.append("Transcript URL:        {}".format(job_info["transcript"]["url"]))

        for item in print_list:
            print(item)

    @property
    def video_title(self):
        """Media info, from customer, title

        :return: Video title given by customer.
        """
        return self.core_metadata.media_title

    def _get_all_detections(self, detection_types=None, n_most_prominent_detections_per_type=float("inf"), **kwargs):
        """List all detections unless type or count is limited

        :param detection_types: Optional, limit method to only yield wanted detection types.
        :type detection_types: str | None
        :param n_most_prominent_detections_per_type: Optional, limit method to yield n first detections.
        :type n_most_prominent_detections_per_type: int | float
        :param kwargs: Not used here yet.
        :return: Generator which yields [detection_id, detection].
        :rtype: Generator[list]
        """
        if n_most_prominent_detections_per_type is None:
            n_most_prominent_detections_per_type = float("inf")

        if not detection_types:
            for detection_type in sorted(self.metadata["detection_groupings"]["by_detection_type"]):
                for detection_id, detection in self._get_all_detections(
                        detection_types=detection_type,
                        n_most_prominent_detections_per_type=n_most_prominent_detections_per_type):
                    # Recursive
                    yield detection_id, detection
        else:
            for det_type in sorted(self.metadata["detection_groupings"]["by_detection_type"]):
                if not _types_match(det_type, detection_types):
                    continue
                count = 0
                for detection_id in self.metadata["detection_groupings"]["by_detection_type"][det_type]:
                    if count >= n_most_prominent_detections_per_type:
                        break
                    yield detection_id, self.metadata["detections"][detection_id]
                    count += 1

    def _get_secdata_interval(self, **kwargs):
        """Returns list containing all by_second data between start_second and end_second.

        :param kwargs: Parameters used here:
            - 'start_second' (int).
            - 'end_second' (int).
        :return: List of second data.
        :rtype: list[list]
        """
        if kwargs.get("end_second") is None:
            secdata_interval = self.metadata["detection_groupings"]["by_second"][kwargs.get("start_second", 0):]
        else:
            secdata_interval = self.metadata["detection_groupings"]["by_second"][
                kwargs.get("start_second", 0): kwargs["end_second"]+1]
        return secdata_interval

    def _detections_by_second(self, **kwargs):
        """Generator which yields each seconds each cell in following format: [sec_index, det_data].

        Limits results with _conditions_match(detection, **kwargs).

        :param kwargs: Parameters used here:
            - 'start_second' (int).
        :return:
        :rtype: Generator[list]
        """
        secdata_interval = self.core_metadata.second_data(
            start_second=kwargs["start_second"],
            end_second=kwargs["end_second"],
        )
        for sec_index, secdata in secdata_interval:
            for detdata in secdata:
                detection_id = detdata["d"]
                detection = self.metadata["detections"][detection_id]
                if not _conditions_match(detection, **kwargs):
                    continue
                yield sec_index, detdata

    def _get_labels_by_second(self, **kwargs):
        """Output just second with labels

        Format: [second, label,label,...]
        """
        index = kwargs.get("start_second", 0)
        for second in self._get_secdata_interval(**kwargs):
            labels = [index]
            for occ in second:
                if kwargs.get("detection_type") and\
                        self.metadata["detections"][occ["d"]]["t"] not in kwargs.get("detection_type"):
                    continue
                if kwargs.get("min_confidence") and occ.get("c") and kwargs["min_confidence"] > occ["c"]:
                    # Test for confidence on that second.
                    continue
                if not _min_confidence_match(self.metadata["detections"][occ["d"]], kwargs.get("min_confidence")):
                    continue
                label = self.metadata["detections"][occ["d"]]["label"]
                labels.append(label)

            yield labels
            index += 1

    def get_subtitle_data(self, start=0, stop=None, det_type=None):
        """Yields data needed for label-subtitle generation

        :param start: The starting second.
        :type start: int or float
        :param stop: The final second (default: till end of video)
        :type stop: int or float or None
        :param list det_type: List of detection types to whitelist.
        :return: Yields [start, stop, label/name].
        :rtype: Generator[list]
        """
        for secdata in self.get_all_occs_by_second_data(start, stop, det_type):
            detection = self.metadata["detections"][secdata["d"]]
            # Get start and stop times for detection:
            for occ in detection["occs"]:  # Find the occ
                if occ["id"] == secdata["o"][0]:
                    start = occ["ss"]
                    stop = occ["se"]
            # Generate label:
            if "a" in detection and detection["t"] == "human.face":
                # human.face (most likely?)
                label = _person_name(detection)

            elif "label" in detection:
                label = detection["label"]
            else:
                raise RuntimeError("No 'a' or 'label' in detection")
            yield [start, stop, label]

    def get_all_occs_by_second_data(self, start=0, stop=None, det_type=None):
        """Yields every second of metadata unless limited.

        :param start: The starting second.
        :type start: int or float
        :param stop: The final second (default: till end of video)
        :type stop: int or float or None
        :param list det_type: List of detection types to whitelist.
        :return: Yields data from metadata["detection_groupings"]["by_second"] structure.
        :rtype: Generator[dict]
        """
        if stop is None:
            # Make sure that stop is bigger than index
            stop = float('inf')
        index = start
        for second in self.metadata["detection_groupings"]["by_second"][start:]:
            if index > stop:
                break
            for secdata in second:
                if det_type and self.metadata["detections"][secdata["d"]]["t"] not in det_type:
                    continue
                yield secdata


def _detection_type_specific_information(detection):
    """Returns information specific to detection type

    :param dict detection: A detection object from metadata["detections"].
    :return: Potentially useful information specific to detection type.
    """
    info = ""
    if detection["t"] == "human.face":
        attrs = detection["a"]
        info += "Gender: " + attrs["gender"]["value"] + " with confidence: " + str(
            attrs["gender"]["c"]) + ". "
        if "similar_to" in attrs:
            for similar in attrs["similar_to"]:
                # info += "Similar to person: {} with confidence: {}.".format(similar["name"], str(similar["c"]))
                info += "Similar to person: " + similar["name"] + " with confidence: " + str(
                    similar["c"]) + "."
    elif detection["t"].startswith("topic.iab."):
        info += "IAB ID: " + detection["ext_refs"]["iab"]["id"] + ". "
        # info += "IAB hierarchical label structure: " + str(detection["ext_refs"]["iab"]["labels_hierarchy"]) + ". "
    return info


def _conditions_match(detection, count=None, **kwargs):
    """Testing detection against given optional parameters.
    """
    # --n-most-prominent-detections-per-type N
    if count is not None and kwargs.get("n_most_prominent_detections_per_type") is not None and \
            count >= kwargs["n_most_prominent_detections_per_type"]:
        return False
    # --detection-types TYPES
    if kwargs.get("detection_types") is not None and not \
            _types_match(detection["t"], kwargs["detection_types"]):
        return False
    # --detection-labels LABELS
    if kwargs.get("detection_label") is not None and not \
            _label_match(detection["label"], kwargs["detection_label"]):
        return False
    # --detection-persons PERSONS
    if kwargs.get("detection_persons") is not None and not \
            _person_match(detection, kwargs["detection_persons"]):
        return False
    # --detection-valossa-cid CID
    if kwargs.get("detection_valossa_cid") is not None and not \
            _valossa_concept_id_match(detection, kwargs["detection_valossa_cid"]):
        return False
    # --detection-external-concept-id ONTOLOGY ID
    if kwargs.get("detection_external_concept_id") is not None and not \
            _external_concept_id_match(detection, kwargs["detection_external_concept_id"]):
        return False
    # --min-confidence X
    if kwargs.get("min_confidence") is not None and not \
            _min_confidence_match(detection, kwargs["min_confidence"]):
        return False
    # --category x y z
    if kwargs.get("category") is not None:
        if "categ" not in detection or "tags" not in detection["categ"] or \
                not set(detection["categ"]["tags"]) & set(kwargs["category"]):
            return False
    return True


def _min_confidence_match(detection, min_confidence):
    """Test against confidence level

    Currently tests confidence against `similar_to` person
    or `occs` `c_max`.

    Returns `True` if confidence is high enough.
    """
    if min_confidence is None:
        return True
    if "a" in detection and "similar_to" in detection["a"]:
        for similar in detection["a"]["similar_to"]:
            if similar["c"] >= min_confidence:
                return True
        return False
    if "a" in detection and "gender" in detection["a"]:
        if detection["a"]["gender"]["c"] >= min_confidence:
            return True
    if "occs" in detection:
        for occ in detection["occs"]:
            if "c_max" in occ:
                if occ["c_max"] >= min_confidence:
                    return True
            elif detection["t"] == "human.face_group":
                # human.face does not have confidence if it does not have similar_to field.
                # human.face_group does not have confidence.
                return False
            else:
                # print >> sys.stderr, "Warning: Confidence field not found for {}.".format(detection.get('label'))
                # What is our wanted behaviour when there is no confidence field?
                return False
    return False


def _types_match(det_type, type_list):
    """If types match, return True, else False

    :param det_type:
    :type det_type: str
    :param type_list:
    :type type_list: list
    :return:
    :rtype: bool
    """
    if det_type in type_list:
        return True
    else:
        return False


def _label_match(label, arg):
    """Used to check if arg is in labels list.

    :param arg: User given argument
    :return: Boolean value True if matched, False otherwise
    """

    return arg == label


def _person_match(detection, args):
    """
    `detection` is the single detection cell
    `args` can be either `all` or comma separated string of persons.
    eg. "Brad Pitt","George Clooney"
    Windcards aren't supported and names are case-sensitive (at the moment).
    Returns `True` if match is found.
    """

    if "a" not in detection:
        return False
    if "similar_to" not in detection["a"]:
        return False
    # if args == "all":
    #    return True

    nameList = [x["name"] for x in detection["a"]["similar_to"]]
    argList = [x.strip() for x in args.split(',')]
    if True in [_wildcard_search(keyarg, name) for keyarg in argList for name in nameList]:
        return True
    return False


def _old_concept_id_match(detection, searchArg):
    """Accepts both Valossa Concept ID and GKG Concept ID"""

    # b = ("cid" in detection) or ("ext_refs" in detection and "gkg" in detection["ext_refs"])
    ids = []
    if "cid" in detection:
        ids.append(detection["cid"])
    if "ext_refs" in detection and "gkg" in detection["ext_refs"]:
        ids.append(detection["ext_refs"]["gkg"]["id"])

    if searchArg in ids:
        return True
    return False


def _external_concept_id_match(detection, ontology_and_concept_id):
    """Accepts both Valossa Concept ID and GKG Concept ID"""

    ontology, concept_id = ontology_and_concept_id
    if "ext_refs" in detection and ontology in detection["ext_refs"]:
        if concept_id == detection["ext_refs"][ontology]["id"]:
            return True
    return False


def _valossa_concept_id_match(detection, id_arg):
    """Accepts both Valossa Concept ID and GKG Concept ID"""

    if "cid" in detection:
        if id_arg == detection["cid"]:
            return True
    return False


def _wildcard_search(keyword, det_cell):
    """If keyword in list: True
    """
    wildcard = False
    keylist = keyword.split("*")
    for key in keylist:
        index = det_cell.find(key)
        if index == -1:  # -1 means no matches
            return False
        if index > 0 and wildcard is False:
            return False
        det_cell = det_cell[index+len(key):]
        wildcard = True
    # If last character was not wildcard and there are characters left in det_cell
    # then there isn't match:
    if key != "" and det_cell != "":
        return False
    return True


def _person_name(detection, detection_id=None, confidence=False):
    if detection["t"] != "human.face":  # Has to be human.face
        return ""
    if "similar_to" in detection["a"]:
        if confidence:
            return detection["a"]["similar_to"][0]["c"], detection["a"]["similar_to"][0]["name"]
        else:
            return detection["a"]["similar_to"][0]["name"]
    elif "gender" in detection["a"]:
        label = "unknown {}".format(detection["a"]["gender"]["value"])
    else:
        label = "unknown person"
    if detection_id is not None:
        label += " (det ID: {})".format(detection_id)
    if confidence:
        return None, label
    return label


def _person_gender(detection):
    if "a" in detection and "gender" in detection["a"]:
        return detection["a"]["gender"]["value"]
    else:
        return ""

def _textregion_text(detection):
    if "a" in detection and "text" in detection["a"]:
        return detection["a"]["text"]["as_one_string"]
    else:
        return ""

def _seconds_to_timestamp_hhmmss(seconds_from_beginning):
    """Generates timestamp from inputted seconds

    :param seconds_from_beginning: Seconds to generate timestamp from
    :return: Timestamp in form HH:MM:SS
    """
    hours = seconds_from_beginning // 3600
    s = seconds_from_beginning - (hours * 3600)
    minutes = s // 60
    seconds = s - (minutes * 60)
    return '%02d:%02d:%02d' % (hours, minutes, seconds)
