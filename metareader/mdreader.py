# -*- coding: utf-8 -*-
"""Metadata-reader

This module contains all functions, classes etc. to read Valossa Core metadata.
"""

import sys
from decimal import Decimal  # Division by 20 causes rounding behaviour, which isn't pretty.


class AppError(Exception):
    """Custom error to catch so that we don't catch some other error by mistake."""


class MetadataReader(object):
    def __init__(self, metadata_json):
        self.metadata = metadata_json

    def list_detections(self, **kwargs):
        """Yields csv-format list rows.

        First row is the csv header containing following labels:

        * detection ID
        * detection type
        * label
        * Valossa concept ID
        * GKG concept ID
        * more information


        :param kwargs: Arguments are just passed forward here.
        :return: Generator which yields one row at time.
        :rtype: Generator[list]
        """

        yield ["detection ID", "detection type", "label", "Valossa concept ID", "GKG concept ID", "more information"]
        for det_id, detection in self._get_all_detections(**kwargs):

            # Limit listing:
            if not _conditions_match(detection, **kwargs):
                continue

            vco_id = ""
            if "cid" in detection:
                vco_id = detection["cid"]
            gkg_id = ""
            if "ext_refs" in detection and "gkg" in detection["ext_refs"]:
                gkg_id = detection["ext_refs"]["gkg"]["id"]
            more_info = _detection_type_specific_information(detection)

            yield [det_id,                 # Detection ID
                   detection["t"],         # Detection type
                   detection["label"],     # Label
                   vco_id,                 # Valossa Concept ID
                   gkg_id,                 # GKG Concept ID
                   more_info,              # More information
                   ]

    def list_detections_by_second(self, **kwargs):
        """List detections by second

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

        Output headers (srt):

        * start
        * stop
        * line of labels


        :param kwargs: Keyword arguments used here:
            - 'output_format' (str). If 'srt, use self.list_subtitle() -generator.
            - 'min_confidence' (float). Valossa Core metadata has confidence values between 0.5 and 1.0 so we encourage
              to use values between those in this argument, or None.
        :return: Generator which yields one row at time.
        :rtype: Generator[list]
        """

        if kwargs.get("output_format") == "srt":
            # Output subtitles
            for item in self.list_subtitle(**kwargs):
                yield item
        else:
            # Default procedure
            yield ["second", "timestamp", "detection ID", "detection type", "confidence", "label", "Valossa concept ID",
                   "GKG concept ID", "more information"]
            for sec_index, detdata in self._detections_by_second(**kwargs):
                detection_id = detdata["d"]
                detection = self.metadata["detections"][detection_id]
                vco_id = ""
                if "cid" in detection:
                    vco_id = detection["cid"]
                gkg_id = ""
                if "ext_refs" in detection and "gkg" in detection["ext_refs"]:
                    gkg_id = detection["ext_refs"]["gkg"]["id"]
                confidence = ""
                if "c" in detdata:
                    # TESTING FOR ARGS.MIN_CONFIDENCE
                    if kwargs.get("min_confidence", None) and detdata["c"] < kwargs.get("min_confidence"):
                        continue
                    confidence = detdata["c"]

                more_info = _detection_type_specific_information(detection)
                yield [sec_index,                                       # Second-index
                       _seconds_to_timestamp_hhmmss(sec_index),         # Timestamp
                       detection_id,                                    # Detection ID
                       detection["t"],                                  # Detection type
                       confidence,                                      # Confidence
                       unicode(detection["label"]).encode("utf-8"),     # Label
                       vco_id,                                          # Valossa Concept ID
                       gkg_id,                                          # GKG Concept ID
                       unicode(more_info).encode("utf-8")]              # More information

    def list_subtitle(self, delta=0.5, min_sub_interval=2, **kwargs):
        """Subtitle does not allow limiters at this time.

        :param delta: The higher the delta, the later the subtitles show up compared to occurrence.
        :param min_sub_interval: Minimum time to show each subtitle.
        :param kwargs: Arguments used here:
            - 'start_second' (int).
            - 'end_second' (int).
            - 'detection_types' (string).
        :return: Yields subtitles one field at time.
        :rtype: Generator[list]
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
        sub_data_gen = self.get_subtitle_data(
            start=kwargs.get("start_second"),
            stop=kwargs.get("end_second"),
            det_type=kwargs.get("detection_types"),
        )
        last_end_time = -space
        subtitle_labels = []
        for start, stop, label in sub_data_gen:
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

                yield [start_time, end_time] + line_labels

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

            yield [start_time, end_time] + line_labels

            # Remove old labels:
            last_end_time = end_time
            subtitle_labels = [x for x in subtitle_labels if x[1] >= end_time - delta]
            if not subtitle_labels:
                break
            s_min, s_max = min_max(subtitle_labels, 0)

    def list_summary(self, **kwargs):
        """Method to gather list containing summary.

        :param kwargs: Arguments used here:
            - 'detection_type' (string).
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
        :rtype: Generator[dict[str, list]]
        """
        detection_type = kwargs.pop("detection_type", None)
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

        if detection_type == "human.face":
            if "human.face" in self.metadata["detection_groupings"]["by_detection_type"]:
                for detection_id in self.metadata["detection_groupings"]["by_detection_type"][detection_type]:
                    detection = self.metadata["detections"][detection_id]
                    if "similar_to" in detection["a"]:

                        screentime = LengthSum(add_type)
                        for occ in detection["occs"]:
                            # human.face doesn't have occ confidence
                            screentime.add(occ["ss"], occ["se"])

                        # Take first cell, as it's most accurate:
                        cell = detection["a"]["similar_to"][0]
                        if kwargs.get("min_confidence") and cell["c"] < kwargs.get("min_confidence"):
                            continue
                        summ_dict[detection_type]["{}".format(detection_id)] = [
                            cell['name'],                   # 0 : name_or_label
                            screentime,                     # 1 : screentime
                            cell['c'],                      # 2 : confidence
                            float(screentime)/video_length  # 3 : of video length
                        ]
                    else:
                        # UNKNOWN PERSON
                        if kwargs.get("skip_unknown_faces", None):
                            continue
                        screentime = LengthSum(add_type)
                        for occ in detection["occs"]:
                            screentime.add(occ["ss"], occ["se"])
                        summ_dict[detection_type]["{}".format(detection_id)] = [
                            "unknown {} (det id: {})".format(detection["a"]["gender"]["value"], detection_id),  # 0 : name_or_label
                            float(screentime),                                       # 1 : screentime
                            '-',                                                     # 2 : confidence
                            float(screentime) / video_length                         # 3 : of video length
                        ]

                #
                # Combine identities:
                if not kwargs.get("separate_face_identities", False):
                    new_dict = {detection_type: dict()}
                    face_dict = dict()
                    for id, item in summ_dict[detection_type].iteritems():
                        if item[0].startswith("unknown"):
                            new_dict[detection_type][id] = item
                            continue
                        if item[0] in face_dict:
                            face_dict[item[0]][1][1].add(item[1])  # Screentime
                            face_dict[item[0]][1][2] = min(face_dict[item[0]][1][2], item[2])  # Confidence
                            face_dict[item[0]][1][3] = face_dict[item[0]][1][1] / video_length  # of vid. len.
                        else:
                            face_dict[item[0]] = id, item

                    for id, face in face_dict.itervalues():
                        new_dict[detection_type][id] = face
                    summ_dict = new_dict

        else:
            if detection_type in self.metadata["detection_groupings"]["by_detection_type"]:
                for detection_id in self.metadata["detection_groupings"]["by_detection_type"][detection_type]:
                    detection = self.metadata["detections"][detection_id]
                    # TESTING FOR CONFIDENCE
                    if kwargs.get("min_confidence") and not _min_confidence_match(detection, kwargs.get("min_confidence")):
                        continue
                    screentime = LengthSum(add_type)
                    for occ in detection["occs"]:
                        # TESTING (again) FOR CONFIDENCE
                        if kwargs.get("min_confidence") and occ["c_max"] < kwargs.get("min_confidence"):
                            continue
                        screentime.add(occ["ss"], occ["se"])

                    summ_dict[detection_type][detection_id] = [
                        detection["label"],                 # 0 : name_or_label
                        screentime,                         # 1 : screentime
                        float(screentime) / video_length    # 2 : of video length
                    ]

        # Sort and limit by n-most-prominent-detections-per-type
        count = 0
        n_first = kwargs.get("n_most_prominent_detections_per_type", None)
        if n_first is None:
            n_first = float('inf')
        summ_list = {detection_type: list()}
        for item in sorted(summ_dict[detection_type].itervalues(),
                           key=lambda v: float(v[1]),
                           reverse=True):
            if detection_type == "human.face":
                item[1] = "{:.3f}".format(float(item[1]))  # remove float calculation errors
            else:
                # Labels etc. have one second resolution
                item[1] = "{:.1f}".format(float(item[1]))  # remove float calculation errors
            if count >= n_first:
                break
            count += 1
            summ_list[detection_type].append(item)
        yield dict(summary=summ_list)

    def metadata_info(self):
        """Outputs info about given metadata-file

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

        print_list = list()
        print_list.append(u"Metadata format:  {}".format(versions["metadata_format"]))
        print_list.append(u"Backend version:  {}".format(versions["backend"]))
        print_list.append(u"")

        # MEDIA_INFO

        print_list.append(u"Media title:      {}".format(media_info["from_customer"]["title"]))
        print_list.append(u"Duration:         {}".format(_seconds_to_timestamp_hhmmss(media_info["technical"]["duration_s"])))
        if job_info["description"] is None:
            description = u"-"  # Better than just u"None"
        else:
            description = job_info["description"]
        print_list.append(u"Description:      {}".format(description))
        print_list.append(u"")

        if job_info["video"]["url"] is not None:
            print_list.append(u"Video URL:        {}".format(job_info["video"]["url"]))
        if job_info["transcript"]["url"] is not None:
            print_list.append(u"Video URL:        {}".format(job_info["transcript"]["url"]))

        for item in print_list:
            print item

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
        if kwargs.get("end_second", None) is None:
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
        secdata_interval = self._get_secdata_interval(**kwargs)
        sec_index = kwargs.get("start_second", 0) - 1
        for secdata in secdata_interval:
            sec_index += 1
            for detdata in secdata:
                detection_id = detdata["d"]
                detection = self.metadata["detections"][detection_id]
                if not _conditions_match(detection, **kwargs):
                    continue
                yield sec_index, detdata

    def get_subtitle_data(self, start=0, stop=None, det_type=None):
        """Yields data needed for subtitle generation

        Format: [start, stop, label/name]
        """
        for secdata in self.get_all_occs_by_second_data(start, stop, det_type):
            detection = self.metadata[u"detections"][secdata[u"d"]]
            # Get start and stop times for detection:
            for occ in detection[u"occs"]:  # Find the occ
                if occ[u"id"] == secdata[u"o"][0]:
                    start = occ[u"ss"]
                    stop = occ[u"se"]
            # Generate label:
            if "a" in detection:
                if "similar_to" in detection["a"]:
                    label = detection["a"]["similar_to"][0]["name"]
                elif "gender" in detection["a"]:
                    label = "unknown {}".format(detection["a"]["gender"]["value"])
                else:
                    label = "unknown person"

            elif "label" in detection:
                label = detection["label"]
            else:
                raise RuntimeError("No 'a' or 'label' in detection")
            yield [start, stop, label]

    def get_all_occs_by_second_data(self, start=0, stop=None, det_type=None):
        """yields every second of metadata unless limited"""
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
    """Returns information specific to detection type"""
    info = ""
    if detection["t"] == "human.face":
        attrs = detection["a"]
        info += "Gender: " + attrs["gender"]["value"] + " with confidence: " + str(
            attrs["gender"]["c"]) + ". "
        if "similar_to" in attrs:
            for similar in attrs["similar_to"]:
                info += "Similar to person: " + similar["name"] + " with confidence: " + str(
                    similar["c"]) + "."
    elif detection["t"].startswith("topic.iab."):
        info += "IAB ID: " + detection["ext_refs"]["iab"]["id"] + ". "
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
    return True


def _min_confidence_match(detection, min_confidence):
    """Test against confidence level

    Currently tests confidence against `similar_to` person
    or `occs` `c_max`.

    Returns `True` if confidence is high enough.
    """
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


def _types_match(det_type, type_arg):
    """
    Method tests for asterix wildcard '*'.
    Supported positions for wildcards are following:
       "*something"
       "something*"
       "*something*"
    Method isn't quite robust yet.
    """

    arg_list = [x.strip() for x in type_arg.split(',')]
    if True in [_wildcard_search(key_arg, det_type) for key_arg in arg_list]:
        return True
    return False


def _label_match(label, arg):
    """Checks if arg is in labels list.

    :param label_list: List of labels
    :param arg: User given argument
    :return: Boolean value True if matched, False otherwise
    """

    return arg == label

    # Seperate by comma and strip leading and trailing whitespace:
    # labelList = [x.strip() for x in labels.split(',')]
    # arg_list = [x.strip() for x in args.split(',')]
    # if True in [_wildcard_search(keyarg, label) for keyarg in arg_list for label in label_list]:
    #    return True
    # return False

    # One-line version:
    # return True in [_wildcard_search(k,l) for k in [x.strip() for x in args.split(',')] for l in [x.strip() for x in labels.split(',')]]


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


class LengthSum(object):
    """Class to allow changing addition type.

    Union type addition simply extends time range when adding

    Normal type addition just adds end-start each time
    """
    def __init__(self, sum_type="normal"):
        self.compress_flag = False
        if sum_type == "union":
            self.add = self.add_union
            self.sum_type = "union"
            self.intervals = []
        elif sum_type == "normal":
            self.add = self.add_normal
            self.sum_type = "normal"
            self.sum = 0.0
        else:
            raise TypeError("sum_type must be either union or normal")

    def __str__(self):
        return str(self.__float__())

    def __repr__(self):
        return repr(self.__float__())

    def __float__(self):
        if self.compress_flag:
            self.intervals = self.compress(self.intervals)
        if self.sum_type == "union":
            r_sum = 0.0
            for interval in self.intervals:
                r_sum += interval[1] - interval[0]
            return r_sum
        return self.sum

    def __div__(self, other):
        return self.__float__() / other

    def add_union(self, ss, se=None):
        # If trying to add self, do nothing:
        if ss is self:
            pass
        elif se is None and type(ss) == LengthSum:
            for interval in ss.intervals:
                self.intervals.append(interval)
        else:
            self.intervals.append((ss, se))
        self.compress_flag = True

    def add_normal(self, ss, se=None):
        if se is None and type(ss) == LengthSum:
            self.sum += ss.sum
        else:
            self.sum += se - ss

    @staticmethod
    def compress(source_list):
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
