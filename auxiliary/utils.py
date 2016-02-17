def parse_boolean(boolean_input):
    if not boolean_input or boolean_input in ['False', 'false', False]:
        return False

    elif boolean_input in ['True', 'true', True]:
        return True

    else:
        return boolean_input
