"""Past-only eligibility and training preparation; future holding prices are not consulted."""
from collections import Counter

from app.schemas.portfolio import PortfolioRequest
from app.services.analysis import carbon_value, financial
from app.services.portfolio import PortfolioError
from app.services.portfolio_data import prepare
from app.services.preparation import align_emissions, day


def portfolio_config(config,window,ids):
    return PortfolioRequest(
        data_mode=config.data_mode,company_ids=ids,start_date=window["training_start"],end_date=window["training_end"],
        as_of=window["decision_date"],risk_aversion=config.risk_aversion,carbon_penalty=config.carbon_penalty,
        long_gross=config.long_gross,short_gross=config.short_gross,max_weight=config.max_weight,
        min_assets=config.min_assets,min_candidates=config.min_candidates,min_observations=config.min_observations,
        shrinkage=config.shrinkage)


def membership(data,cid,decision):
    events=[e for e in data["membership_events"] if e["company_id"]==cid and day(e["published"])<decision
            and day(e["effective"])<=decision]
    if not events:
        return False
    events.sort(key=lambda e:(day(e["effective"]),day(e["published"])))
    if len(events)>1 and (events[-1]["effective"],events[-1]["published"])==(events[-2]["effective"],events[-2]["published"]):
        raise ValueError("Ambiguous historical universe events")
    return events[-1]["active"]


def at_decision(data,config,window):
    decision=window["decision_date"]
    companies=[c for c in data["companies"] if (not config.company_ids or c["id"] in config.company_ids)
               and (not config.sectors or c["sector"] in config.sectors)]
    exclusions={};chosen={};eligible=[]
    for c in companies:
        cid=c["id"]
        try:
            if not membership(data,cid,decision):
                raise ValueError("Not in documented contemporaneous universe")
            specs=[s for s in data["reviews"].get(str(cid),[]) if day(s["known_from"])<decision]
            specs.sort(key=lambda s:day(s["known_from"]))
            if not specs or (len(specs)>1 and specs[-1]["known_from"]==specs[-2]["known_from"]):
                raise ValueError("No unambiguous price/source review available before decision")
            spec=specs[-1]
            if not spec.get("historical_price_vintage_verified") or not spec.get("evidence"):
                raise ValueError("Historical price/corporate-action vintage not verified")
            calendar=[day(d) for d in spec["expected_dates"] if window["training_start"]<=day(d)<=window["training_end"]]
            # Never inspect any price >= decision when deciding eligibility or ranking candidates.
            rows=[dict(p,date=day(p["date"])) for p in data["prices"] if p["company_id"]==cid and
                  p["source_id"]==spec["price_source_id"] and window["training_start"]<=day(p["date"])<=window["training_end"]]
            fin=financial(rows,expected_dates=calendar,adjustment_verified=spec["adjustment_verified"],
                          min_daily_returns=config.min_observations)
            if fin["status"]!="computable":
                raise ValueError("Insufficient complete adjusted training history")
            stream=[e for e in data["emissions"] if e["company_id"]==cid and e["source_id"]==spec["emission_source_id"]
                    and e["methodology"]==spec["methodology"] and e.get("scope2_basis")=="market-based"]
            emission=align_emissions([dict(company_id=cid,synthetic=data["synthetic"],date=decision)],stream)[0]["emission"]
            if emission is None:
                raise ValueError("No prior publicly available carbon disclosure")
            value,issue=carbon_value(emission,"scope1+2","market-based")
            if issue or value is None or any(emission.get(s+"_status")!="reported" for s in ("scope1","scope2")):
                raise ValueError("Missing/incompatible reported Scope1 + market-based Scope2")
            eligible.append(cid);chosen[str(cid)]=spec
        except (ValueError,KeyError,TypeError) as exc:
            exclusions[str(cid)]=str(exc)
    if len(eligible)<config.min_assets:
        raise PortfolioError(f"{decision}: only {len(eligible)} eligible securities; need {config.min_assets}. Exclusions: {exclusions}","insufficient")
    pc=portfolio_config(config,window,eligible)
    selected={**data,"reviews":chosen}
    prepared,ready=prepare(selected,pc)
    if prepared is None:
        raise PortfolioError(f"{decision}: {'; '.join(ready['blockers'])}",ready["status"])
    # Holding accounting uses exactly the declared common session intervals; no omitted calendar sessions allowed.
    for cid in eligible:
        local=[day(d) for d in chosen[str(cid)]["expected_dates"] if window["training_start"]<=day(d)<=window["training_end"]]
        if local[0]!=window["training_start"] or local[-1]!=window["training_end"]:
            raise PortfolioError("Training calendar endpoint mismatch","insufficient")
    return dict(window=window,prepared=prepared,readiness=ready,configuration=pc,reviews=chosen,exclusions=exclusions)


def inventory(data,config):
    ids={c["id"] for c in data["companies"] if (not config.company_ids or c["id"] in config.company_ids)
         and (not config.sectors or c["sector"] in config.sectors)}
    prices=[p for p in data["prices"] if p["company_id"] in ids]
    blockers=[]
    if config.company_ids and set(config.company_ids)-{c["id"] for c in data["companies"]}:
        blockers.append("Selected securities are not available in this dataset mode")
    if not config.min_assets<=len(ids)<=40:
        blockers.append(f"Need {config.min_assets}–40 distinct selected securities; have {len(ids)}")
    if not any(p.get("adjusted_close") is not None for p in prices):
        blockers.append("No eligible adjusted daily price history")
    if not data.get("membership_history_verified") or not data.get("membership_events") or not data.get("universe_reference"):
        blockers.append("Historical membership or documented historical research universe is unverified; a 2026 snapshot is insufficient")
    if not data.get("calendar"):
        blockers.append("No reviewed historical session calendar")
    if not data.get("reviews"):
        blockers.append("No point-in-time source/corporate-action and disclosure-vintage reviews")
    if data.get("coverage_start") and (day(data["coverage_start"])>config.start_date or day(data["coverage_end"])<config.end_date):
        blockers.append("Historical universe coverage does not span evaluation dates")
    return dict(status="insufficient",synthetic=data["synthetic"],provenance=data["provenance"],blockers=blockers,
                company_count=len(ids),price_count=len(prices),adjusted_price_count=sum(p.get("adjusted_close") is not None for p in prices),
                scheduled_periods=0,decision_dates=[],exclusions=dict(Counter()))
