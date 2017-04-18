#!/usr/bin/env python
# -*-coding: utf8 -*-

import warnings
import tokenize
from token import tok_name
from StringIO import StringIO
from pygments.lexers.c_cpp import CppLexer
from pygments.lexers.javascript import JavascriptLexer
from pygments.lexers.jvm import JavaLexer
from pygments.lexers.python import PythonLexer
from multiprocessing import Process, Queue, cpu_count

# import copy_reg
# import types
#
# def _reduce_method(m):
#     if m.im_self is None:
#         return getattr, (m.im_class, m.im_func.func_name)
#     else:
#         return getattr, (m.im_self, m.im_func.func_name)
# copy_reg.pickle(types.MethodType, _reduce_method)


def in_any(token_type, ignore_types):
    return any([token_type in ignore_type
                for ignore_type in ignore_types])


def worker(input, output):
    for func, args in iter(input.get, 'STOP'):
        result = func(*args)
        output.put(result)

def do_task(tokenizer, i, code_line_chunk, return_types, ignore_types):
    result = tokenizer.tokenize(code_line_chunk, return_types=return_types,
                                ignore_types=ignore_types)
    return (i, result)

class CodeChunkTokenizer():

    def __init__(self, language="python"):
        """

        :param language: python, javascript, java or cpp
        """
        self.language = language
        if self.language == "python":
            self.lexer = PythonLexer()
        elif self.language == "javascript":
            self.lexer = JavascriptLexer()
        elif self.language == "cpp":
            self.lexer = CppLexer()
        elif self.language == "java":
            self.lexer = JavaLexer()
        else:
            raise NotImplementedError

    def tokenize(self, code_lines, return_types=False, ignore_types=()):
        #if self.language == "python":
        #    return self._python_tokenize(code_lines, return_types=return_types, ignore_types=ignore_types)
        if self.language in ["python", "javascript", "cpp", "java"]:
            return self._pygment_tokenize(code_lines, return_types=return_types, ignore_types=ignore_types)
        else:
            raise NotImplementedError

    def _pygment_tokenize(self, code_lines, return_types=False, ignore_types=()):
        """
        :param code_lines:
        :param return_types:
        :param ignore_types:
        :return:
        """
        try:
            code = "".join([code_line.decode('ascii', errors='ignore')
                            for code_line in code_lines])
            types, tokens= zip(*[(ttype, token) for ttype, token in self.lexer.get_tokens(code)
                                  if not in_any(ttype, ignore_types)])
            if return_types:
                return tokens, types
            else:
                return tokens
        except Exception as e:
            warnings.warn(str(e))
            return []

    def _python_tokenize(self, code_lines, return_types=False, ignore_types=()):
        """
        """
        code = '\n'.join(code_lines)
        tokens = tokenize.generate_tokens(StringIO(code).readline)
        tokens_types = []
        try:
            # http://stackoverflow.com/questions/1769332/script-to-remove-python-comments-docstrings
            prev_toktype = tokenize.INDENT
            for tok in tokens:
                token_type = tok[0]
                token_string = tok[1]
                start_line, start_col = tok[2]
                # skip ignered:
                if token_type in ignore_types:
                    pass
                # This series of conditionals removes docstrings:
                elif tokenize.COMMENT in ignore_types \
                        and token_type == tokenize.STRING:
                    if prev_toktype != tokenize.INDENT:
                        # This is likely a docstring; double-check we're not inside an operator:
                        if prev_toktype != tokenize.NEWLINE:
                            # Catch whole-module docstrings:
                            if start_col > 0:
                                # Unlabelled indentation means we're inside an operator
                                tokens_types.append((token_string, token_type))
                else:
                    tokens_types.append((token_string, token_type))
                prev_toktype = token_type

        except Exception as e:
            warnings.warn(str(e))
            return []

        tokens, types = zip(*tokens_types)
        if return_types:
            return tokens, map(tok_name.__getitem__, types)
        return tokens

    def batch_tokenize(self, code_line_chunks, ignore_types=(), num_processes=cpu_count()):

        results = [None] * len(code_line_chunks)

        NUMBER_OF_PROCESSES = num_processes
        TASKS = [(do_task, (self, i, code_line_chunk, False, ignore_types))
                  for i, code_line_chunk in  enumerate(code_line_chunks)]

        # Create queues
        task_queue = Queue()
        done_queue = Queue()

        processes_container = []
        # Start worker processes
        for i in range(NUMBER_OF_PROCESSES):
            p = Process(target=worker, args=(task_queue, done_queue))
            processes_container.append(p)
            p.start()

        # Submit tasks
        for task in TASKS:
            task_queue.put(task)

        # Get and print results
        for _ in range(len(TASKS)):
            i, result = done_queue.get()
            results[i] = result

        # Tell child processes to stop
        for i in range(NUMBER_OF_PROCESSES):
            task_queue.put('STOP')

        for process in processes_container:
            process.terminate()

        return results

class CodeLinesTokenizer():

    def __init__(self, language="python"):
        """

             :param language: python, javascript, java or cpp
             """
        self.language = language
        if self.language == "python":
            self.lexer = PythonLexer()
        elif self.language == "javascript":
            self.lexer = JavascriptLexer()
        elif self.language == "cpp":
            self.lexer = CppLexer()
        elif self.language == "java":
            self.lexer = JavaLexer()
        else:
            raise NotImplementedError

    def tokenize(self, code_lines, return_types=False, ignore_types=()):
        #if self.language == "python":
        #    return self._python_tokenize(code_lines, return_types=return_types, ignore_types=ignore_types)
        if self.language in ["python", "javascript", "cpp", "java"]:
            return self._pygment_tokenize(code_lines, return_types=return_types, ignore_types=ignore_types)
        else:
            raise NotImplementedError

    def _pygment_tokenize(self, code_lines, return_types=False, ignore_types=()):
        """
        Recommended ignore_types ('LINE_COMMENT', 'BLOCK_COMMENT'
        :param code_lines:
        :param return_types:
        :param ignore_types:
        :return:
        """
        tokens = []
        types = []
        for code_line in code_lines:
            try:
                code_line = code_line.strip().decode('utf-8').encode('ascii', 'replace')
                ttypes, ttokens = zip(*[(ttype, token) for ttype, token in self.lexer.get_tokens(code_line)
                                        if not in_any(ttype, ignore_types)])
                tokens += ttokens
                if return_types:
                    types += ttypes
            except Exception as e:
                warnings.warn(str(e))
        if return_types:
            return tokens, types
        else:
            return tokens

    def _python_tokenize(self, code_lines, return_types=False, ignore_types=()):
        """
        """
        all_tokens_types = []
        for line in code_lines:
            #line = line.decode('utf-8').encode('ascii', 'replace')
            tokens = tokenize.generate_tokens(StringIO(line).readline)
            try:
                # http://stackoverflow.com/questions/1769332/script-to-remove-python-comments-docstrings
                prev_toktype = tokenize.INDENT
                for tok in tokens:
                    token_type = tok[0]
                    token_string = tok[1]
                    start_line, start_col = tok[2]
                    # skip ignered:
                    if token_type in ignore_types:
                        pass
                    # This series of conditionals removes docstrings:
                    elif tokenize.COMMENT in ignore_types \
                    and token_type == tokenize.STRING:
                        if prev_toktype != tokenize.INDENT:
                            # This is likely a docstring; double-check we're not inside an operator:
                            if prev_toktype != tokenize.NEWLINE:
                                # Catch whole-module docstrings:
                                if start_col > 0:
                                    # Unlabelled indentation means we're inside an operator
                                    all_tokens_types.append((token_string, token_type))
                    else:
                        all_tokens_types.append((token_string, token_type))
                    prev_toktype = token_type

            except Exception as e:
                warnings.warn(str(e))

        if all_tokens_types:
            tokens, types = zip(*all_tokens_types)
            if return_types:
                return tokens, map(tok_name.__getitem__, types)
            return tokens
        else:
            return []

    def batch_tokenize(self, code_line_chunks, ignore_types=(), num_processes=cpu_count()):

        results = [None] * len(code_line_chunks)

        NUMBER_OF_PROCESSES = num_processes
        TASKS = [(do_task, (self, i, code_line_chunk, False, ignore_types))
                 for i, code_line_chunk in enumerate(code_line_chunks)]

        # Create queues
        task_queue = Queue()
        done_queue = Queue()

        processes_container = []
        # Start worker processes
        for i in range(NUMBER_OF_PROCESSES):
            p = Process(target=worker, args=(task_queue, done_queue))
            processes_container.append(p)
            p.start()

        # Submit tasks
        for task in TASKS:
            task_queue.put(task)

        # Get and print results
        for _ in range(len(TASKS)):
            i, result = done_queue.get()
            results[i] = result

        # Tell child processes to stop
        for i in range(NUMBER_OF_PROCESSES):
            task_queue.put('STOP')

        for process in processes_container:
            process.terminate()

        return results


                # def _js_tokenize(self, code_lines, return_types=False, ignore_types=()):
#     """
#     Recommended ignore_types ('LINE_COMMENT', 'BLOCK_COMMENT'
#     :param code_lines:
#     :param return_types:
#     :param ignore_types:
#     :return:
#     """
#     try:
#         code = "".join([code_line.decode('ascii', errors='ignore')
#                         for code_line in code_lines])
#         self.lexer.input(code)
#         tokens, types = zip(*[(token.value, token.type) for token in self.lexer
#                               if token.type not in ignore_types])
#         if return_types:
#             return tokens, types
#         else:
#             return tokens
#     except Exception as e:
#         warnings.warn(str(e))
#         return []

# def _js_tokenize(self, code_lines, return_types=False, ignore_types=()):
#     """
#     Recommended ignore_types ('LINE_COMMENT', 'BLOCK_COMMENT'
#     :param code_lines:
#     :param return_types:
#     :param ignore_types:
#     :return:
#     """
#     tokens = []
#     types = []
#     for code_line in code_lines:
#         try:
#             self.lexer.input(code_line.strip().decode('utf-8').encode('ascii', 'replace'))
#             ttokens, ttypes = zip(*[(token.value, token.type) for token in self.lexer
#                                     if token.type not in ignore_types])
#             tokens += ttokens
#             if return_types:
#                 types += ttypes
#         except Exception as e:
#             warnings.warn(str(e))
#     if return_types:
#         return tokens, types
#     else:
#         return tokens