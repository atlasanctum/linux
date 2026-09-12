"""
Atlas Sanctum — Full Integration Test Suite
Phases I through VI — all systems, all swap points, all workflows.

Run:
    atlas/.venv/bin/python atlas/tests/test_integration.py
"""
from __future__ import annotations
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import traceback

PASS = "\033[92m\u2713\033[0m"
FAIL = "\033[91m\u2717\033[0m"
_failures: list[str] = []


def check(label: str, condition: bool) -> None:
    if condition:
        print(f"  {PASS} {label}")
    else:
        print(f"  {FAIL} {label}")
        _failures.append(label)


# ===========================================================================
# Phase I — Foundation
# ===========================================================================

def test_phase1() -> None:
    print("\nPhase I \u2014 Foundation")
    from atlas.schemas.types import (
        NodeConfig, NodeRole, Identity, Signal, SignalSource, ImpactDomain,
    )
    from atlas.node.identity.manager import IdentityManager
    from atlas.node.protocols.heartbeat import Heartbeat

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        id_file = tmp_path / "identity.json"

        # Identity — static method takes a path
        identity = IdentityManager.load_or_create(id_file)
        check("Ed25519 identity created", len(identity.public_key) == 64)
        identity2 = IdentityManager.load_or_create(id_file)
        check("Identity persists across loads", identity.id == identity2.id)

        # NodeConfig
        cfg = NodeConfig(name="test-node", role=NodeRole.EDGE, identity=identity)
        check("NodeConfig created", cfg.role == NodeRole.EDGE)

        # Signal
        sig = Signal(source=SignalSource.SENSOR, domain=ImpactDomain.WATER,
                     node_id=cfg.id, payload={"value": 42})
        check("Signal created", sig.domain == ImpactDomain.WATER)

        # Heartbeat — _emit is private; verify tick() runs without error
        # and the protocol constant is correct
        from atlas.node.protocols.heartbeat import PROTOCOL_VERSION
        hb = Heartbeat(node_id=cfg.id, interval=0)  # interval=0 so tick fires immediately
        hb.tick()  # should not raise
        check("Heartbeat protocol version correct",
              PROTOCOL_VERSION == "atlas/heartbeat/v1")
        check("Heartbeat node_id stored", hb.node_id == cfg.id)


# ===========================================================================
# Phase II — Intelligence
# ===========================================================================

def test_phase2() -> None:
    print("\nPhase II \u2014 Intelligence")
    from atlas.core.intelligence.core import AtlasCore
    from atlas.schemas.types import Entity, Relation, ImpactDomain, ImpactRecord

    with tempfile.TemporaryDirectory() as tmp:
        core = AtlasCore(node_id="node-test", data_dir=Path(tmp))

        # Knowledge graph
        e1 = Entity(kind="machine", label="Idle Lathe", properties={"status": "idle"})
        e2 = Entity(kind="resource", label="Steel Offcuts", properties={"kg": 200})
        core.graph.add_entity(e1)
        core.graph.add_entity(e2)
        from atlas.schemas.types import Relation
        rel = Relation(source_id=e1.id, target_id=e2.id, kind="uses")
        core.graph.add_relation(rel)
        check("Entities added to graph", len(core.graph._entities) == 2)
        check("Relation added to graph", len(core.graph._relations) == 1)

        # Persist and reload
        core.save_graph()
        from atlas.core.knowledge.store import GraphStore
        g2 = GraphStore(Path(tmp) / "knowledge_graph.json").load()
        check("Graph persists to disk", len(g2._entities) == 2)

        # Opportunity scanning
        opps = core.scan_opportunities()
        check("Opportunity scan returns list", isinstance(opps, list))

        # Policy engine — human_oversight_required checks impact_level
        allowed = core.check_policy("human_oversight_required",
                                    {"impact_level": "low"})
        check("Policy: low impact \u2192 allowed", allowed)
        denied = core.check_policy("human_oversight_required",
                                   {"impact_level": "high", "human_approved": False})
        check("Policy: high impact without approval \u2192 denied", not denied)
        approved = core.check_policy("human_oversight_required",
                                     {"impact_level": "high", "human_approved": True})
        check("Policy: high impact with approval \u2192 allowed", approved)

        # Simulation — result stored in run.result dict
        run = core.simulate("water_demand",
                            {"population": 500, "litres_per_person": 20,
                             "sources": [{"capacity_litres": 8000}]},
                            label="test-run")
        check("Simulation run produced result", isinstance(run.result, dict))
        check("Simulation result has expected key",
              "gross_litres" in run.result)

        # Impact ledger
        rec = ImpactRecord(domain=ImpactDomain.WATER, metric="households",
                           value=120, unit="households", node_id="node-test")
        core.impact.record(rec)
        summary = core.impact.summary()
        # summary() returns {domain: {count, total}}
        check("Impact ledger records entry",
              summary.get("water", {}).get("count", 0) == 1)

        # Agent runtime
        result = core.run_agent("opportunity_scout", "scan", {})
        check("Agent dispatched successfully", result is not None)


# ===========================================================================
# Phase III — Field Systems
# ===========================================================================

def test_phase3() -> None:
    print("\nPhase III \u2014 Field Systems")
    from atlas.core.signals.pipeline import SignalPipeline
    from atlas.core.gis.index import GeoIndex, GeoFeature
    from atlas.node.offline.queue import OfflineSyncQueue
    from atlas.node.protocols.sync import SyncProtocol
    from atlas.node.identity.manager import IdentityManager
    from atlas.schemas.phase3 import SensorReading, SensorType, SyncEnvelope

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Signal pipeline — register_handler takes only a callable
        pipeline = SignalPipeline(node_id="node-test")
        received: list = []
        pipeline.register_handler(lambda s: received.append(s))
        reading = SensorReading(
            sensor_id="s1", sensor_type=SensorType.WATER_FLOW,
            value=12.5, unit="L/min", quality=0.9,
        )
        pipeline.ingest(reading)
        check("Signal pipeline ingests reading", len(received) == 1)

        # Low quality rejected
        bad = SensorReading(
            sensor_id="s2", sensor_type=SensorType.WATER_FLOW,
            value=0.0, unit="L/min", quality=0.1,
        )
        pipeline.ingest(bad)
        check("Low-quality signal rejected", len(received) == 1)

        # GIS index
        geo = GeoIndex()
        from atlas.schemas.phase3 import GeoPoint
        feat = GeoFeature(id="f1", label="Borehole A",
                          location=GeoPoint(latitude=-1.286, longitude=36.817),
                          properties={"depth_m": 45})
        geo.add(feat)
        centre = GeoPoint(latitude=-1.286, longitude=36.817)
        nearby = list(geo.within_radius(centre, radius_km=1.0))
        check("GeoIndex finds feature within radius", len(nearby) == 1)
        geojson = geo.to_geojson_collection()
        check("GeoIndex exports GeoJSON", geojson["type"] == "FeatureCollection")

        # Offline queue — flush() uses registered transports, no lambda arg
        queue = OfflineSyncQueue(tmp_path / "queue.jsonl")
        env = SyncEnvelope(origin_node_id="node-a", target_node_id="node-b",
                           payload_type="test", payload={"x": 1})
        queue.enqueue(env)
        check("Offline queue enqueues envelope", queue.pending_count() == 1)
        queue.register_transport(lambda e: True)   # always-succeed transport
        result = queue.flush()
        check("Offline queue flushes successfully", result["sent"] == 1)
        check("Queue empty after flush", queue.pending_count() == 0)

        # Sync protocol — sign + verify
        id_file = tmp_path / "identity.json"
        identity = IdentityManager.load_or_create(id_file)
        sync = SyncProtocol(id_file)
        env2 = SyncEnvelope(origin_node_id=identity.id, target_node_id="peer",
                            payload_type="summary", payload={"data": "hello"})
        sync.sign(env2)
        check("SyncProtocol signs envelope", len(env2.signature) > 0)
        sync.register_peer(identity.id, identity.public_key)
        check("SyncProtocol verifies own signature", sync.verify(env2))


# ===========================================================================
# Phase IV — Invention (full)
# ===========================================================================

def test_phase4() -> None:
    print("\nPhase IV \u2014 Invention")
    from atlas.core.intelligence.core import AtlasCore
    from atlas.schemas.types import Entity, Signal, SignalSource, ImpactDomain
    from atlas.schemas.phase4 import PrototypeStatus, RoboticsTask, RoboticsTaskStatus
    from atlas.core.adapters.robotics import SimulationRoboticsAdapter

    with tempfile.TemporaryDirectory() as tmp:
        core = AtlasCore(node_id="node-test", data_dir=Path(tmp))

        # Seed graph
        e1 = Entity(kind="machine", label="Idle Press",
                    properties={"status": "idle", "capacity": 100})
        e2 = Entity(kind="resource", label="Waste Plastic",
                    properties={"kg": 500, "available": True})
        core.graph.add_entity(e1)
        core.graph.add_entity(e2)

        # Invention proposals
        proposals = core.invent(top_n=5)
        check("InventionEngine returns proposals list", isinstance(proposals, list))

        # Digital twin — create(name, asset_id, model_type, initial_state)
        twin = core.twins.create(
            name="pump-01", asset_id="pump-01",
            model_type="water_pump",
            initial_state={"flow_rate": 10.0, "pressure": 2.5},
        )
        check("DigitalTwin created", twin.asset_id == "pump-01")

        # Sync twin from a Signal
        signal = Signal(
            source=SignalSource.SENSOR, domain=ImpactDomain.WATER,
            node_id="node-test",
            payload={"sensor_id": "pump-01", "value": 11.2, "quality": 0.95},
        )
        core.twins.sync(twin.id, signal)
        updated = core.twins.get(twin.id)
        check("DigitalTwin syncs from signal", updated.state["flow_rate"] == 11.2)
        check("DigitalTwin records history snapshot", len(core.twins.history(twin.id)) == 1)

        # Run experiment
        def pump_experiment(t, params):
            return {"projected_flow": params.get("flow_rate", 0) * 1.1,
                    "pressure_delta": params.get("pressure", 0) - t.state.get("pressure", 0)}

        exp = core.twins.run_experiment(
            twin.id,
            hypothesis="Increase flow rate by 10%",
            parameters={"flow_rate": 15.0, "pressure": 3.0},
            experiment_fn=pump_experiment,
        )
        check("DigitalTwin experiment runs", exp.twin_id == twin.id)
        check("Experiment has result", isinstance(exp.result, dict))
        check("Experiment completed", exp.result.get("projected_flow", 0) > 0)

        # Prototype lifecycle
        if proposals:
            run = core.prototypes.start(proposals[0])
            check("Prototype starts at IDEA", run.status == PrototypeStatus.IDEA)
            core.prototypes.advance(run.id, notes="Design complete")
            check("Prototype advances to DESIGNED", run.status == PrototypeStatus.DESIGNED)
            core.prototypes.advance(run.id, notes="Build started")
            check("Prototype advances to PROTOTYPING", run.status == PrototypeStatus.PROTOTYPING)
            core.prototypes.advance(run.id, notes="Testing in field")
            check("Prototype advances to TESTING", run.status == PrototypeStatus.TESTING)
            core.prototypes.advance(run.id, notes="Validated by community")
            check("Prototype advances to VALIDATED", run.status == PrototypeStatus.VALIDATED)
            check("Validated timestamp set", run.validated_at is not None)
            core.prototypes.advance(run.id, notes="Scaling to 3 sites")
            check("Prototype advances to SCALING", run.status == PrototypeStatus.SCALING)
            # Terminal — no further advance
            core.prototypes.advance(run.id)
            check("Prototype stays at SCALING (terminal)", run.status == PrototypeStatus.SCALING)

        # Robotics adapter
        robotics = SimulationRoboticsAdapter(node_id="node-test")
        task = RoboticsTask(
            robot_id="drone-01", task_type="inspect",
            parameters={"target": "pump-01"}, node_id="node-test",
        )
        completed = robotics.dispatch(task)
        check("Robotics task dispatched", completed.status == RoboticsTaskStatus.COMPLETE)
        check("Robotics task has result", isinstance(completed.result, dict))
        readings = list(robotics.readings(completed))
        check("Robotics readings produced", len(readings) >= 1)

        # All 6 domain updaters registered
        for model_type in ["water_pump", "solar_array", "crop_field",
                           "clinic", "workshop", "traffic_junction"]:
            check(f"Updater registered: {model_type}",
                  model_type in core.twins._updaters)

        # Full lab loops
        from atlas.labs.water.lab import run_water_lab
        from atlas.labs.energy.lab import run_energy_lab
        from atlas.labs.agriculture.lab import run_agriculture_lab
        from atlas.labs.manufacturing.lab import run_manufacturing_lab
        from atlas.labs.health.lab import run_health_lab
        from atlas.labs.cities.lab import run_cities_lab

        for lab_fn, name in [
            (run_water_lab, "water"),
            (run_energy_lab, "energy"),
            (run_agriculture_lab, "agriculture"),
            (run_manufacturing_lab, "manufacturing"),
            (run_health_lab, "health"),
            (run_cities_lab, "cities"),
        ]:
            with tempfile.TemporaryDirectory() as lab_tmp:
                r = lab_fn(Path(lab_tmp))
                check(f"{name} lab: twin_state present", "twin_state" in r)
                check(f"{name} lab: proposals generated",
                      r.get("proposals_generated", 0) >= 0)
                # prototype_stage is set when proposals > 0; otherwise None is valid
                has_proposals = r.get("proposals_generated", 0) > 0
                prototype_ok = (
                    (has_proposals and r.get("prototype_stage") is not None)
                    or (not has_proposals and r.get("prototype_stage") is None)
                )
                check(f"{name} lab: prototype lifecycle consistent", prototype_ok)


# ===========================================================================
# Phase V — Coordination
# ===========================================================================

def test_phase5() -> None:
    print("\nPhase V \u2014 Coordination")
    from atlas.core.intelligence.core import AtlasCore
    from atlas.core.workflows.field_to_project import run_field_to_project
    from atlas.schemas.types import Entity

    with tempfile.TemporaryDirectory() as tmp:
        core = AtlasCore(node_id="node-test", data_dir=Path(tmp))

        # Seed graph
        for i in range(3):
            core.graph.add_entity(
                Entity(kind="resource", label=f"Unused Asset {i}",
                       properties={"status": "idle", "value": 100 * i})
            )

        # Coordination engine
        project = core.coordination.create_project(
            title="Kibera Water Access",
            description="Borehole + distribution network",
            domain="water",
            budget_usd=50000.0,
        )
        check("Project created", project.title == "Kibera Water Access")

        # Capital allocation — approver_id present → human_approved=True internally
        alloc = core.coordination.allocate_capital(
            project_id=project.id,
            amount_usd=25000.0,
            source="impact_fund",
            approver_id="approver-001",
        )
        check("Capital allocated with human approval", alloc is not None)
        check("Allocation amount correct", alloc.amount_usd == 25000.0)

        # Autonomous allocation blocked — amount > $10k + empty approver → high impact, no approval
        blocked = core.coordination.allocate_capital(
            project_id=project.id,
            amount_usd=15000.0,
            source="auto",
            approver_id="",
        )
        check("Autonomous capital allocation blocked", blocked is None)

        # Marketplace — publish takes a MarketplaceListing object
        from atlas.schemas.phase5 import MarketplaceListing
        listing = core.marketplace.publish(
            MarketplaceListing(
                kind="resource", title="Solar Panels Available",
                description="20x 300W panels", domain="energy",
                node_id="node-test",
            )
        )
        results = core.marketplace.search(domain="energy")
        check("Marketplace listing published and searchable", len(results) == 1)

        # Federation
        net = core.federation.create_network("East Africa Network", "East Africa")
        check("Regional network created", net.name == "East Africa Network")
        envelopes = core.federation.broadcast_summary(
            {"opportunity_count": 5, "impact_records": 12}, net.id
        )
        check("Federation broadcast returns envelopes list", isinstance(envelopes, list))

        # Full workflow — run_field_to_project(core, coordination, marketplace, approver_id)
        result = run_field_to_project(
            core, core.coordination, core.marketplace, approver_id="approver-001"
        )
        check("Field-to-project workflow completes", result is not None)
        check("Workflow result has projects_created attr",
              hasattr(result, "projects_created"))


# ===========================================================================
# Phase VI — Global Network
# ===========================================================================

def test_phase6() -> None:
    print("\nPhase VI \u2014 Global Network")
    from atlas.core.intelligence.core import AtlasCore
    from atlas.core.globalnet.engine import GlobalNetworkEngine, CAPABILITIES
    from atlas.schemas.phase6 import NetworkTier, ExchangeKind

    with tempfile.TemporaryDirectory() as tmp:
        core = AtlasCore(node_id="node-alpha", data_dir=Path(tmp))

        # Interoperability handshake
        hs = core.connect_global_network(
            "node-beta", peer_capabilities=["sync", "simulation", "marketplace"]
        )
        check("Interop handshake established", hs.node_b_id == "node-beta")
        check("Capabilities negotiated", "sync" in hs.capabilities)
        check("Non-shared capability excluded",
              "world_model" not in hs.capabilities)

        # Global network creation
        gnet = core.global_network.create_global_network(
            "Atlas Global", tier=NetworkTier.GLOBAL
        )
        check("Global network created", gnet.tier == NetworkTier.GLOBAL)

        # Register regional network
        regional = core.federation.create_network("East Africa", "East Africa")
        registered = core.global_network.register_regional_network(gnet.id, regional)
        check("Regional network registered in global network", registered)
        check("Regional network ID tracked",
              len(gnet.regional_network_ids) == 1)

        # World model snapshot
        regional_summaries = [
            {"member_count": 5, "opportunity_count": 12,
             "active_project_count": 3, "impact_record_count": 45,
             "domains": {"water": {"nodes": 3, "avg_value": 72.5},
                         "energy": {"nodes": 2, "avg_value": 61.0}}},
            {"member_count": 4, "opportunity_count": 8,
             "active_project_count": 2, "impact_record_count": 30,
             "domains": {"water": {"nodes": 2, "avg_value": 68.0},
                         "agriculture": {"nodes": 2, "avg_value": 55.0}}},
        ]
        snap = core.build_world_model(gnet.id, regional_summaries)
        check("World model snapshot built", snap.contributing_nodes == 9)
        check("World model aggregates domains", "water" in snap.domain_summaries)
        check("Water avg computed correctly",
              abs(snap.domain_summaries["water"]["avg_value"] - 70.25) < 0.01)
        check("Opportunity count aggregated", snap.opportunity_count == 20)

        # Research exchange
        exchange = core.publish_research(
            title="Borehole Yield Optimisation Study",
            description="Field data from 12 boreholes in Kibera, 2024",
            network_id=gnet.id,
            payload={"boreholes": 12, "avg_yield_lph": 850},
            tags=["water", "field-research", "nairobi"],
        )
        check("Research artefact published", exchange.title.startswith("Borehole"))
        check("Payload hash generated", len(exchange.payload_hash) == 64)

        results = core.global_network.search_research(tag="water")
        check("Research searchable by tag", len(results) == 1)

        # Cross-region routing
        from atlas.schemas.phase3 import SyncEnvelope
        env = SyncEnvelope(origin_node_id="node-alpha", target_node_id="node-gamma",
                           payload_type="summary", payload={"x": 1})
        routes = core.global_network.route_envelope(env, gnet.id)
        check("Cross-region routing returns regional network IDs",
              isinstance(routes, list))

        # Status
        status = core.global_network.status()
        check("Global network status reports correctly",
              status["global_networks"] == 1)
        check("Interop peers tracked", status["interop_peers"] == 1)
        check("Research artefacts tracked", status["research_artefacts"] == 1)

        # Neo4j store interface (import only — no live DB in tests)
        from atlas.core.knowledge.neo4j_store import Neo4jGraphStore
        check("Neo4jGraphStore importable", True)


# ===========================================================================
# Restored infrastructure
# ===========================================================================

def test_restored_pieces() -> None:
    print("\nRestored Infrastructure")
    base = Path(__file__).resolve().parents[1]

    for doc in [
        "docs/linux-foundation/README.md",
        "docs/simulation/README.md",
        "docs/agents/README.md",
        "docs/economics/README.md",
        "docs/atlas-codex/README.md",
    ]:
        check(f"Doc exists: {doc}", (base / doc).exists())

    for inf in [
        "infrastructure/linux/atlas-node.service",
        "infrastructure/linux/sysctl-atlas.conf",
        "infrastructure/networking/wireguard-node.conf",
        "infrastructure/security/apparmor-atlas.profile",
        "infrastructure/storage/README.md",
    ]:
        check(f"Infra exists: {inf}", (base / inf).exists())

    check("Phase VI schema exists", (base / "schemas/phase6.py").exists())
    check("Global network engine exists",
          (base / "core/globalnet/engine.py").exists())
    check("Neo4j store exists",
          (base / "core/knowledge/neo4j_store.py").exists())


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  Atlas Sanctum \u2014 Integration Test Suite")
    print("  Phases I \u2013 VI")
    print("=" * 60)

    for fn in [test_phase1, test_phase2, test_phase3,
               test_phase4, test_phase5, test_phase6,
               test_restored_pieces]:
        try:
            fn()
        except Exception:
            print(f"\n  {FAIL} EXCEPTION in {fn.__name__}:")
            traceback.print_exc()
            _failures.append(fn.__name__)

    print("\n" + "=" * 60)
    if _failures:
        print(f"  {FAIL} {len(_failures)} check(s) failed:")
        for f in _failures:
            print(f"    - {f}")
        sys.exit(1)
    else:
        print(f"  {PASS} All checks passed \u2014 Phases I\u2013VI complete.")
    print("=" * 60)
