"""에러 관리 및 표준 에러 메시지 모듈.

[실생활 비유]
  매장 안내 데스크의 표준 안내 문구표입니다.
  손님이 없는 메뉴를 부르거나, 옵션 개수를 틀리거나, 숫자가 아닌 값을 입력하거나,
  창고 용량(maxmemory)을 초과했을 때 항상 Redis 표준 규격에 맞는 일관된 안내 문구를 반환합니다.
"""


# ===== 1구역: 예외 클래스 =====
class OOMError(Exception):
    """단일 키+값 크기가 maxmemory 한도를 넘어 저장 자체가 불가능할 때 발생하는 예외."""


# ===== 2구역: Redis 표준 에러 문자열 =====
ERR_INT = "(error) ERR value is not an integer or out of range"
ERR_OOM = "(error) OOM command not allowed when used_memory > 'maxmemory'"


def err_unknown_command(command_name):
    """지원하지 않는 명령어가 입력되었을 때 반환할 표준 에러 문자열."""
    return "(error) ERR unknown command '%s'" % command_name


def err_wrong_arity(command_name):
    """명령어에 필요한 인자 개수가 맞지 않을 때 반환할 표준 에러 문자열."""
    return "(error) ERR wrong number of arguments for '%s' command" % command_name


def err_unknown_section(section_name):
    """INFO 명령에서 'memory' 외의 알 수 없는 섹션을 요청했을 때 반환할 에러 문자열."""
    return "(error) ERR unknown section '%s'" % section_name


def err_unsupported_config():
    """CONFIG 명령에서 'CONFIG SET maxmemory <N>' 외의 하위 명령이 입력되었을 때 에러 문자열."""
    return "(error) ERR unsupported CONFIG subcommand"
