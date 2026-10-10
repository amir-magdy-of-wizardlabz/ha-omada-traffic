"""Setup and options screens for Omada Traffic."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME, CONF_VERIFY_SSL
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_OMADAC_ID, CONF_SITE_ID, CONF_SITE_NAME, DOMAIN
from .omada_api import OmadaAuthError, OmadaError, discover

NO_LINE = "(all devices, no specific line)"


class OmadaTrafficConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._conn: dict[str, Any] = {}
        self._sites: list[dict[str, str]] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].strip().rstrip("/")
            if "://" not in url:
                url = f"https://{url}"
            try:
                cid, sites = await discover(url, user_input[CONF_USERNAME], user_input[CONF_PASSWORD], user_input[CONF_VERIFY_SSL])
            except OmadaAuthError:
                errors["base"] = "invalid_auth"
            except OmadaError:
                errors["base"] = "cannot_connect"
            else:
                if not sites:
                    errors["base"] = "no_sites"
                else:
                    self._conn = {**user_input, CONF_URL: url, CONF_OMADAC_ID: cid}
                    self._sites = sites
                    if len(sites) == 1:
                        return self._finish(sites[0])
                    return await self.async_step_site()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL, default=(user_input or {}).get(CONF_URL, "https://")): str,
                    vol.Required(CONF_USERNAME, default=(user_input or {}).get(CONF_USERNAME, "")): str,
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    ),
                    vol.Required(CONF_VERIFY_SSL, default=False): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_site(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self._finish(next(s for s in self._sites if s["id"] == user_input[CONF_SITE_ID]))
        return self.async_show_form(
            step_id="site",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SITE_ID): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[selector.SelectOptionDict(value=s["id"], label=s["name"]) for s in self._sites]
                        )
                    )
                }
            ),
        )

    def _finish(self, site: dict[str, str]) -> ConfigFlowResult:
        return self.async_create_entry(
            title=f"Omada ({site['name']})",
            data={**self._conn, CONF_SITE_ID: site["id"], CONF_SITE_NAME: site["name"]},
        )

    async def async_step_import(self, data: dict[str, Any]) -> ConfigFlowResult:
        """Take over an install that was configured in configuration.yaml."""
        return self.async_create_entry(title=f"Omada ({data.get(CONF_SITE_NAME) or 'site'})", data=data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return OmadaTrafficOptionsFlow()


class OmadaTrafficOptionsFlow(OptionsFlow):
    """Edit internet plans, people and the start of the day."""

    def __init__(self) -> None:
        self._editing: int | None = None

    @property
    def _loader(self):
        return self.hass.data[DOMAIN]["settings"]

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        menu = ["add_plan"]
        if self._loader.raw_plans:
            menu += ["edit_plan", "remove_plan"]
        menu += ["people", "general"]
        return self.async_show_menu(step_id="init", menu_options=menu)

    async def _lines(self) -> list[str]:
        """Names of the gateway's WAN ports seen so far."""
        collector = self.hass.data[DOMAIN]["collector"]
        names = await collector.run_db(collector.store.wan_names)
        return [NO_LINE, *sorted({n for n in names.values() if n})]

    async def _plan_form(self, step_id: str, plan: dict[str, Any]) -> ConfigFlowResult:
        lines = await self._lines()
        current = plan.get("wan") if plan.get("wan") in lines else NO_LINE
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(
                {
                    vol.Required("name", default=plan.get("name", "")): str,
                    vol.Required("wan", default=current): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=lines, mode=selector.SelectSelectorMode.DROPDOWN)
                    ),
                    vol.Required("quota_gb", default=plan.get("quota_gb", 0)): vol.All(vol.Coerce(float), vol.Range(min=0)),
                    vol.Required("renewal_day", default=plan.get("renewal_day", 1)): vol.All(vol.Coerce(int), vol.Range(min=1, max=28)),
                    vol.Optional("baseline_date", description={"suggested_value": plan.get("baseline_date")}): selector.DateSelector(),
                    vol.Optional("baseline_gb", default=plan.get("baseline_gb", 0)): vol.All(vol.Coerce(float), vol.Range(min=0)),
                }
            ),
        )

    @staticmethod
    def _clean(user_input: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": user_input["name"].strip() or "Internet plan",
            "wan": None if user_input["wan"] == NO_LINE else user_input["wan"],
            "quota_gb": user_input["quota_gb"],
            "renewal_day": user_input["renewal_day"],
            "baseline_date": user_input.get("baseline_date") or None,
            "baseline_gb": user_input.get("baseline_gb") or 0,
        }

    async def async_step_add_plan(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._loader.set_plans([*self._loader.raw_plans, self._clean(user_input)])
            return self.async_create_entry(data={})
        return await self._plan_form("add_plan", {})

    async def async_step_edit_plan(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        plans = self._loader.raw_plans
        if user_input is not None:
            self._editing = int(user_input["plan"])
            return await self.async_step_plan_details()
        return self.async_show_form(step_id="edit_plan", data_schema=self._pick(plans))

    async def async_step_plan_details(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        plans = self._loader.raw_plans
        if user_input is not None:
            plans[self._editing] = self._clean(user_input)
            self._loader.set_plans(plans)
            return self.async_create_entry(data={})
        return await self._plan_form("plan_details", plans[self._editing])

    async def async_step_remove_plan(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        plans = self._loader.raw_plans
        if user_input is not None:
            del plans[int(user_input["plan"])]
            self._loader.set_plans(plans)
            return self.async_create_entry(data={})
        return self.async_show_form(step_id="remove_plan", data_schema=self._pick(plans))

    @staticmethod
    def _pick(plans: list[dict]) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required("plan"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[selector.SelectOptionDict(value=str(i), label=p["name"]) for i, p in enumerate(plans)]
                    )
                )
            }
        )

    async def async_step_people(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        current = self._loader.get().people
        if user_input is not None:
            wanted = [str(p).strip() for p in user_input.get("people", []) if str(p).strip()]
            for p in current:
                if p not in wanted:
                    self._loader.remove_person(p)
            for p in wanted:
                self._loader.add_person(p)
            return self.async_create_entry(data={})
        return self.async_show_form(
            step_id="people",
            data_schema=vol.Schema(
                {
                    vol.Optional("people", default=current): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=current, multiple=True, custom_value=True)
                    )
                }
            ),
        )

    async def async_step_general(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._loader.set_day_start(int(user_input["day_start_hour"]))
            return self.async_create_entry(data={})
        return self.async_show_form(
            step_id="general",
            data_schema=vol.Schema(
                {
                    vol.Required("day_start_hour", default=str(self._loader.get().day_start_hour)): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=["0", "6"])
                    )
                }
            ),
        )
