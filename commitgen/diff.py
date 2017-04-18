#!/usr/bin/env python
# -*-coding: utf8 -*-


from pygments.lexers import guess_lexer, ClassNotFound
#from guess_language import guess_language
#from langdetect import detect_langs
#from langdetect.lang_detect_exception import LangDetectException



# def is_nl(code_line, threshold=0.9):
#     try:
#         guess_lexer(code_line)
#         return False
#     except ClassNotFound as e:
#         try:
#             if any([gl.prob > threshold for gl in detect_langs(code_line)]):
#                 return True
#         except LangDetectException:
#             return False
#         return False

# def _is_nl(code_line, threshold=0.95):
#     try:
#         if any([gl.prob > threshold for gl in detect_langs(code_line)]):
#             return True
#     except LangDetectException:
#         return False
#     return False

def get_added_lines(parsed_diff_file, marker=None):
    added_lines = []
    for modfile in parsed_diff_file.modified_files:
        if marker:
            added_lines.append(marker)
        for hunk in modfile:
            added_lines += [line.value for line in hunk if line.is_added]
    for addfile in parsed_diff_file.added_files:
        if marker:
            added_lines.append(marker)
        for hunk in addfile:
            added_lines += [line.value for line in hunk if line.is_added]
    return added_lines


def get_removed_lines(parsed_diff_file, marker=None):
    removed_lines = []
    for modfile in parsed_diff_file.modified_files:
        if marker:
            removed_lines.append(marker)
        for hunk in modfile:
            removed_lines += [line.value for line in hunk if line.is_removed]
    for remfile in parsed_diff_file.removed_files:
        if marker:
            removed_lines.append(marker)
        for hunk in remfile:
            removed_lines += [line.value for line in hunk if line.is_removed]
    return removed_lines


class AddRemExtractor(object):

    def __init__(self, marker=None, line_filter=None):
        self.marker=marker
        self.line_filter = line_filter

    def get_lines(self, parsed_diff_file):
        lines = get_added_lines(parsed_diff_file, marker=self.marker) \
                + get_removed_lines(parsed_diff_file, marker=self.marker)
        if self.line_filter:
            return filter(self.line_filter, lines)
        else:
            return lines


class PerFileExtractor(object):

    def __init__(self, marker=None, line_filter=None):
        self.marker = marker
        self.line_filter = line_filter

    def get_lines(self, parsed_diff_file):
        """
        Extract modified, added and removed files ordered by file
        If marker is not None, adds a ghost line with content "marker" to denote the start
        of a new file.

        :param parsed_diff_file:
        :param marker:
        :return:
        """
        modified_lines = []
        for modfile in parsed_diff_file.modified_files:
            if self.marker:
                modified_lines.append(self.marker)
            for hunk in modfile:
                modified_lines += [line.value for line in hunk]
        for addfile in parsed_diff_file.added_files:
            if self.marker:
                modified_lines.append(self.marker)
            for hunk in addfile:
                modified_lines += [line.value for line in hunk]
        for remfile in parsed_diff_file.removed_files:
            if self.marker:
                modified_lines.append(self.marker)
            for hunk in remfile:
                modified_lines += [line.value for line in hunk]
        if self.line_filter:
            return filter(self.line_filter, modified_lines)
        else:
            return modified_lines
