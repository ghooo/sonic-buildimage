import os
import inspect
import ntpath

def get_caller_file_name():
    frame = inspect.stack()[2]
    module = inspect.getmodule(frame[0])
    filename = module.__file__
    without_slash = ntpath.basename(filename)
    return without_slash

def run_command(command):
    # create temp directory to store command output
    stream = os.popen('mkdir -p temp > /dev/null 2>&1; echo $?')
    result = int(stream.read())
    if result:
        raise AttributeError(f'Failed to create temp folder to store command output')

    # run command
    output_file = f"temp/{get_caller_file_name()}.out"
    stream = os.popen(f'{command} > {output_file} 2>&1; echo $?')
    result = int(stream.read())

    stream = os.popen(f'cat {output_file}')
    output = stream.read()

    if result:
        raise AttributeError(f'Apply command failed.\n  Command: {command}\n  Output: {output}')

    return output