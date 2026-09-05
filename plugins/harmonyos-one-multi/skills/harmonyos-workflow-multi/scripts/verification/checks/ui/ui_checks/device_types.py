"""module.json5 的一多目标设备映射与声明校验。"""

from __future__ import annotations

from typing import Iterable, TypedDict


DEFAULT_TARGET_FORMS = ("phone", "foldable", "tablet")
INVALID_DEVICE_TYPES = {"foldable"}


class DeviceTypeRequirement(TypedDict):
    target: str
    anyOf: list[str]


def effective_target_forms(target_forms: Iterable[str]) -> list[str]:
    """未限定设备时返回一多默认三设备，明确限定时保持用户范围。"""
    forms = [str(value).strip() for value in target_forms if str(value).strip()]
    return forms or list(DEFAULT_TARGET_FORMS)


def required_device_type_groups(target_forms: Iterable[str]) -> list[DeviceTypeRequirement]:
    """把任务形态映射为允许多种声明值的设备能力组。"""
    mobile = tablet = False
    for raw_form in effective_target_forms(target_forms):
        form = str(raw_form).strip().lower()
        if any(token in form for token in ("tablet", "pad", "平板")):
            tablet = True
        if any(token in form for token in (
            "default", "phone", "fold", "widefold", "triplefold", "手机", "直板", "折叠",
        )):
            mobile = True
    requirements: list[DeviceTypeRequirement] = []
    if mobile:
        requirements.append({"target": "phone/foldable", "anyOf": ["default", "phone"]})
    if tablet:
        requirements.append({"target": "tablet", "anyOf": ["tablet"]})
    return requirements


def missing_requirements(
    declared: set[str], requirements: Iterable[DeviceTypeRequirement],
) -> list[DeviceTypeRequirement]:
    return [requirement for requirement in requirements if declared.isdisjoint(requirement["anyOf"])]


def module_object(data: object) -> dict | None:
    if not isinstance(data, dict):
        return None
    module = data.get("module")
    return module if isinstance(module, dict) else None


def declaration_errors(module: dict) -> list[str]:
    """返回与任务目标无关、可确定判断的声明错误。"""
    raw = module.get("deviceTypes")
    if not isinstance(raw, list) or not raw or any(not isinstance(value, str) or not value for value in raw):
        return ["module.deviceTypes 必须是非空字符串数组"]
    invalid = sorted({value for value in raw if value in INVALID_DEVICE_TYPES})
    if invalid:
        return [
            "module.deviceTypes 不使用 foldable；手机或折叠屏按工程配置使用 phone 或 default"
        ]
    return []


def declared_device_types(module: dict) -> set[str]:
    raw = module.get("deviceTypes")
    if not isinstance(raw, list):
        return set()
    return {value for value in raw if isinstance(value, str) and value}
