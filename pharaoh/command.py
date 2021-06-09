commands = []


def Command(func):
    func.__command__ = True
    commands.append(commands)
    return func
