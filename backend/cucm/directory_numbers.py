def normalise_directory_number_pattern(pattern: str) -> str:
    if pattern.startswith('\\+'):
        return pattern[1:]
    return pattern


def escape_directory_number_pattern(pattern: str) -> str:
    normalised_pattern = normalise_directory_number_pattern(pattern)
    if normalised_pattern.startswith('+'):
        return f'\\{normalised_pattern}'
    return normalised_pattern


def directory_number_pattern_variants(pattern: str) -> tuple[str, str]:
    normalised_pattern = normalise_directory_number_pattern(pattern)
    escaped_pattern = escape_directory_number_pattern(normalised_pattern)
    return (normalised_pattern, escaped_pattern)