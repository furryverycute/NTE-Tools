from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any

from app.data import (
    BASE_TRAFFIC,
    COFFEE_BEAN_TREND,
    COFFEE_BEAN_TREND_ITEMS,
    DEFAULT_TREND_BONUS,
    EMPLOYEE_NAMES,
    FRUIT_INGREDIENTS,
    MENU_ATTRS,
    RAW_ITEMS,
    SKILL_RAW,
    STORE_NAMES,
)


@dataclass(frozen=True)
class MenuItem:
    id: int
    name: str
    attr: str
    base_price: float
    level: int
    ingredients: tuple[str, ...]

    @property
    def display_name(self) -> str:
        return f"{self.name} Lv.2" if self.level == 2 else self.name


@dataclass(frozen=True)
class Employee:
    name: str
    level: int
    skills: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class Pick:
    store_name: str
    employees: tuple[str, str]
    menu: MenuItem
    final_price: float
    income: float
    trend_applied: bool


@dataclass(frozen=True)
class CafeResult:
    picks: tuple[Pick, ...]
    active_skills: tuple[str, ...]
    all_skill_logs: tuple[str, ...]
    tag_counts: dict[str, int]
    traffic: int
    exact_traffic: float
    price_fixed: float
    cond_price_fixed: float
    cond_price_percent: float
    traffic_fixed: float
    cond_traffic_percent: float
    final_total: float
    interior_mult: float
    trend_value: float
    shop_count: int

    @property
    def final_total_with_interior(self) -> float:
        return self.final_total * self.interior_mult

    @property
    def price_bonus_text(self) -> str:
        fixed = self.price_fixed + self.cond_price_fixed
        percent = self.cond_price_percent * 100
        return f"고정 +{fixed:.2f} / 비율 +{percent:.1f}%"

    @property
    def traffic_bonus_text(self) -> str:
        return f"고정 +{self.traffic_fixed:.0f} / 비율 +{self.cond_traffic_percent * 100:.1f}%"


class CafeOptimizerEngine:
    @staticmethod
    def get_shop_count(level: int) -> int:
        if level >= 25:
            return 5
        if level >= 17:
            return 4
        if level >= 10:
            return 3
        if level >= 5:
            return 2
        return 1

    @staticmethod
    def get_available_items(level: int) -> list[MenuItem]:
        items: list[MenuItem] = []
        for row in RAW_ITEMS:
            if level < row[4]:
                continue
            item_level = 2 if level >= row[6] else 1
            base_price = row[5] if item_level == 2 else row[3]
            items.append(MenuItem(int(row[0]), row[1], row[2], float(base_price), item_level, tuple(row[7] or [])))
        return items

    @staticmethod
    def get_skill_effects(name: str, level: int) -> tuple[dict[str, Any], ...]:
        effects = []
        for row in SKILL_RAW:
            if row[0] == name and row[1] <= level:
                effects.append({
                    'type': row[2],
                    'value': row[3],
                    'tag': row[4] if len(row) > 4 else None,
                    'num': row[5] if len(row) > 5 else None,
                })
        return tuple(effects)

    @staticmethod
    def is_trend_matched(menu: MenuItem, trend: str) -> bool:
        if not trend:
            return False
        if trend in MENU_ATTRS:
            return menu.attr == trend
        if trend == '과일':
            return any(ingredient in FRUIT_INGREDIENTS for ingredient in menu.ingredients)
        if trend == COFFEE_BEAN_TREND:
            return menu.name in COFFEE_BEAN_TREND_ITEMS
        return trend in menu.ingredients

    @staticmethod
    def _check_condition(tag: str | None, need: int | None, tag_counts: dict[str, int]) -> bool:
        if tag is None or need is None:
            return False
        if tag == 'any':
            return any(count >= need for count in tag_counts.values())
        return tag_counts.get(tag, 0) >= need

    @classmethod
    def compute_buffs(cls, all_skills: list[dict[str, Any]], menu_tag_counts: dict[str, int]) -> dict[str, Any]:
        price_fixed = 0.0
        traffic_fixed = 0.0
        cond_price_fixed = 0.0
        cond_price_percent = 0.0
        cond_traffic_percent = 0.0
        logs: list[str] = []
        active_logs: list[str] = []

        for effect in all_skills:
            effect_type = effect['type']
            value = float(effect['value'])
            tag = effect.get('tag')
            num = effect.get('num')
            if effect_type == 'price_fixed':
                price_fixed += value
                text = f"가격 +{value:.2f}"
                logs.append(f"{text} ✅")
                active_logs.append(text)
            elif effect_type == 'traffic_fixed':
                traffic_fixed += value
                text = f"유동인구 +{value:.0f}"
                logs.append(f"{text} ✅")
                active_logs.append(text)
            elif effect_type == 'cond_price_fixed':
                ok = cls._check_condition(tag, num, menu_tag_counts)
                if ok:
                    cond_price_fixed += value
                text = f"가격 +{value:.2f} ({tag}≥{num})"
                logs.append(f"{text} {'✅' if ok else '❌'}")
                if ok:
                    active_logs.append(text)
            elif effect_type == 'cond_price_percent':
                ok = cls._check_condition(tag, num, menu_tag_counts)
                if ok:
                    cond_price_percent += value
                text = f"가격 +{value * 100:.1f}% ({tag}≥{num})"
                logs.append(f"{text} {'✅' if ok else '❌'}")
                if ok:
                    active_logs.append(text)
            elif effect_type == 'cond_traffic_percent':
                ok = cls._check_condition(tag, num, menu_tag_counts)
                if ok:
                    cond_traffic_percent += value
                text = f"유동인구 +{value * 100:.1f}% ({tag}≥{num})"
                logs.append(f"{text} {'✅' if ok else '❌'}")
                if ok:
                    active_logs.append(text)

        exact_traffic = (BASE_TRAFFIC + traffic_fixed) * (1 + cond_traffic_percent)
        return {
            'price_fixed': price_fixed,
            'traffic_fixed': traffic_fixed,
            'cond_price_fixed': cond_price_fixed,
            'cond_price_percent': cond_price_percent,
            'cond_traffic_percent': cond_traffic_percent,
            'traffic': int(exact_traffic),
            'exact_traffic': exact_traffic,
            'logs': logs,
            'active_logs': active_logs,
        }

    @staticmethod
    def _tag_counts(tags: dict[str, int]) -> dict[str, int]:
        return {'음료': tags['drink'], '디저트': tags['dessert'], '메인 메뉴': tags['main']}

    @staticmethod
    def _tag_combinations(store_count: int) -> list[dict[str, int]]:
        combos: list[dict[str, int]] = []
        for drink in range(store_count + 1):
            for dessert in range(store_count - drink + 1):
                main = store_count - drink - dessert
                combos.append({'drink': drink, 'dessert': dessert, 'main': main})
        return combos

    @classmethod
    def calculate(
        cls,
        shop_level: int,
        trend: str,
        interior_rate: float,
        employee_levels: dict[str, int],
        employee_active: dict[str, bool],
    ) -> CafeResult:
        if shop_level < 1:
            raise ValueError('매장 레벨을 1 이상으로 입력해주세요.')
        if not trend:
            raise ValueError('오늘의 트렌드를 선택해주세요.')

        shop_count = cls.get_shop_count(shop_level)
        active_store_names = STORE_NAMES[:shop_count]
        interior_mult = 1 + max(0.0, interior_rate)
        trend_value = 1.0 if trend in MENU_ATTRS else DEFAULT_TREND_BONUS
        menu_pool = cls.get_available_items(shop_level)
        if not menu_pool:
            raise ValueError('현재 매장 레벨에서 사용할 수 있는 메뉴가 없습니다.')

        available_employees: list[Employee] = []
        for name in EMPLOYEE_NAMES:
            if employee_active.get(name, True) and int(employee_levels.get(name, 0)) > 0:
                level = int(employee_levels.get(name, 0))
                available_employees.append(Employee(name, level, cls.get_skill_effects(name, level)))

        required_employees = shop_count * 2
        dummy_count = 0
        while len(available_employees) < required_employees:
            dummy_count += 1
            available_employees.append(Employee(f'공석{dummy_count}', 0, tuple()))

        def best_items_for_tags(tags: dict[str, int]) -> list[MenuItem] | None:
            selected: list[MenuItem] = []
            needed_by_attr = {'음료': tags['drink'], '디저트': tags['dessert'], '메인 메뉴': tags['main']}
            for attr, needed in needed_by_attr.items():
                if needed == 0:
                    continue
                filtered = [item for item in menu_pool if item.attr == attr]
                filtered.sort(
                    key=lambda item: (
                        item.base_price + (trend_value if cls.is_trend_matched(item, trend) else 0.0),
                        item.base_price,
                    ),
                    reverse=True,
                )
                if len(filtered) < needed:
                    return None
                selected.extend(filtered[:needed])
            return selected

        best_total = -1.0
        best_result: CafeResult | None = None
        emp_combos = combinations(available_employees, required_employees)

        for selected_employees in emp_combos:
            all_skills = [skill for employee in selected_employees for skill in employee.skills]
            names = ['공석' if employee.name.startswith('공석') else employee.name for employee in selected_employees]

            for tags in cls._tag_combinations(shop_count):
                items = best_items_for_tags(tags)
                if items is None:
                    continue

                tag_counts = cls._tag_counts(tags)
                buffs = cls.compute_buffs(all_skills, tag_counts)
                total_income = 0.0
                picks: list[Pick] = []

                for idx, menu in enumerate(items):
                    base = menu.base_price + buffs['price_fixed'] + buffs['cond_price_fixed']
                    trend_applied = cls.is_trend_matched(menu, trend)
                    trend_bonus = trend_value if trend_applied else 0.0
                    final_price = (base + trend_bonus) * (1 + buffs['cond_price_percent'])
                    income = final_price * buffs['exact_traffic'] / 100
                    total_income += income
                    picks.append(Pick(
                        store_name=active_store_names[idx],
                        employees=(names[idx * 2] if idx * 2 < len(names) else '공석', names[idx * 2 + 1] if idx * 2 + 1 < len(names) else '공석'),
                        menu=menu,
                        final_price=final_price,
                        income=income,
                        trend_applied=trend_applied,
                    ))

                if total_income > best_total:
                    best_total = total_income
                    best_result = CafeResult(
                        picks=tuple(picks),
                        active_skills=tuple(sorted(buffs['active_logs'], key=lambda text: (0 if '가격' in text else 1, text))),
                        all_skill_logs=tuple(buffs['logs']),
                        tag_counts=tag_counts,
                        traffic=buffs['traffic'],
                        exact_traffic=buffs['exact_traffic'],
                        price_fixed=buffs['price_fixed'],
                        cond_price_fixed=buffs['cond_price_fixed'],
                        cond_price_percent=buffs['cond_price_percent'],
                        traffic_fixed=buffs['traffic_fixed'],
                        cond_traffic_percent=buffs['cond_traffic_percent'],
                        final_total=total_income,
                        interior_mult=interior_mult,
                        trend_value=trend_value,
                        shop_count=shop_count,
                    )

        if best_result is None:
            raise ValueError('유효한 조합을 찾을 수 없습니다. 직원 수와 매장 레벨을 확인해주세요.')
        return best_result
