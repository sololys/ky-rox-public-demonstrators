class_name LightBridgeActor
extends StaticBody2D

# ==============================================================================
# REALITY FORGE :: GODOT 4 CANONICAL LIGHT BRIDGE ACTOR (LightBridgeActor)
# ==============================================================================
# Invariant Consequence Gate Contract:
# 1. Proposal != Realized Object: Proposing a bridge spawns an immaterial HOLD
#    wireframe with collision disabled and 0.00 V modeled voltage.
# 2. HOLD != delayed OPEN: Time passing never spontaneously opens the gate.
# 3. OPEN requires explicit evidence: A valid, non-empty evidence_id is required.
# 4. Occupancy clearance: Intersecting bodies block realization until confirmed clear.
# 5. KILL guillotine: Immediate 0.00 V cutoff, collision disabled, pending evidence cancelled.
# 6. Reset preserves ledger: RESET appends a record without erasing history.
# 7. Epistemic boundary: All states are modeled software states, not physical proofs.
# ==============================================================================

enum BridgeState {
	HOLD_BLUEPRINT,
	OPEN_REALIZED,
	KILL_ABORTED
}

signal state_transitioned(old_state: BridgeState, new_state: BridgeState, witness_record: Dictionary)
signal occupancy_changed(is_occupied: bool, occupying_count: int)
signal open_deferred_due_to_occupancy(evidence_id: String, reason: String)
signal hold_jurisdiction_escalated(new_jurisdiction: String, elapsed_tau: float, witness_record: Dictionary)

@export var bridge_id: String = "LB-001"
@export var bridge_size: Vector2 = Vector2(340, 24)
@export var hold_tau_max: float = 14.0

# Current runtime state
var current_state: BridgeState = BridgeState.HOLD_BLUEPRINT
var modeled_voltage: float = 0.00
var modeled_voltage_verified: float = 0.00
var is_kill_latched: bool = false
var pulse_timer: float = 0.0
var hold_elapsed_time: float = 0.0
var hold_jurisdiction: String = "P_INT"
var active_hold_delta_k: String = ""
var is_hold_deadline_forfeited: bool = false
var active_evidence_id: String = ""
var last_event_id: String = ""
var last_event_hash: String = "0000000000000000000000000000000000000000000000000000000000000000"

# Occupancy tracking (Area2D)
var overlapping_player_bodies: Array[Node2D] = []
var pending_evidence_for_clearance: Dictionary = {}

# Append-only in-memory witness log (Preserved across resets)
var witness_history: Array[Dictionary] = []

# Node references
@onready var collision_shape: CollisionShape2D = $CollisionShape2D if has_node("CollisionShape2D") else null
@onready var area_detector: Area2D = $Area2D if has_node("Area2D") else null
@onready var visual_rect: ColorRect = $VisualRect if has_node("VisualRect") else null


func _ready() -> void:
	_ensure_child_nodes()
	set_to_hold("INIT_PROPOSAL", "Initial placement of Light Bridge candidate")


func _ensure_child_nodes() -> void:
	# Ensure CollisionShape2D exists
	if not collision_shape:
		if has_node("CollisionShape2D"):
			collision_shape = $CollisionShape2D
		else:
			collision_shape = CollisionShape2D.new()
			collision_shape.name = "CollisionShape2D"
			var box = RectangleShape2D.new()
			box.size = bridge_size
			collision_shape.shape = box
			add_child(collision_shape)

	# Ensure Area2D overlap detector exists
	if not area_detector:
		if has_node("Area2D"):
			area_detector = $Area2D
		else:
			area_detector = Area2D.new()
			area_detector.name = "Area2D"
			var area_shape = CollisionShape2D.new()
			area_shape.name = "AreaShape2D"
			var box_area = RectangleShape2D.new()
			box_area.size = bridge_size + Vector2(4, 12)  # slight margin to detect entering bodies
			area_shape.shape = box_area
			area_detector.add_child(area_shape)
			add_child(area_detector)

	# Connect Area2D signals reliably across scene loads and dynamic creation
	if area_detector:
		area_detector.monitoring = true
		area_detector.monitorable = true
		if not area_detector.is_connected("body_entered", Callable(self, "_on_area_body_entered")):
			area_detector.connect("body_entered", Callable(self, "_on_area_body_entered"))
		if not area_detector.is_connected("body_exited", Callable(self, "_on_area_body_exited")):
			area_detector.connect("body_exited", Callable(self, "_on_area_body_exited"))

	# Ensure Visual representation exists
	if not visual_rect:
		if has_node("VisualRect"):
			visual_rect = $VisualRect
		else:
			visual_rect = ColorRect.new()
			visual_rect.name = "VisualRect"
			visual_rect.size = bridge_size
			visual_rect.position = -bridge_size * 0.5
			add_child(visual_rect)


func _process(delta: float) -> void:
	pulse_timer += delta
	if current_state == BridgeState.HOLD_BLUEPRINT and delta > 0.0:
		advance_hold_clock(delta)
	_update_visuals()


func _update_visuals() -> void:
	if not visual_rect:
		return

	match current_state:
		BridgeState.HOLD_BLUEPRINT:
			# Amber wireframe hologram with low-opacity pulse
			var alpha = 0.32 + 0.18 * sin(pulse_timer * 4.0)
			if is_occupied():
				# Warning accent when player occupies unverified zone
				visual_rect.color = Color(0.98, 0.45, 0.15, alpha + 0.15)
			else:
				visual_rect.color = Color(0.98, 0.75, 0.14, alpha)
		BridgeState.OPEN_REALIZED:
			# Cyan-emerald crystalline hardlight with clean emission
			var pulse = 0.94 + 0.06 * sin(pulse_timer * 2.5)
			visual_rect.color = Color(0.20, 0.85, 0.65, 0.95) * pulse
		BridgeState.KILL_ABORTED:
			# Rapid, clean dissolution (red dissipation cutoff)
			var dissolve_alpha = max(0.0, 0.75 - pulse_timer * 2.5)
			visual_rect.color = Color(0.95, 0.25, 0.37, dissolve_alpha)


# ------------------------------------------------------------------------------
# OCCUPANCY DETECTOR (Area2D Physics Server Overlap)
# ------------------------------------------------------------------------------
func is_occupied() -> bool:
	return overlapping_player_bodies.size() > 0


func _on_area_body_entered(body: Node2D) -> void:
	if body != self and (body.is_in_group("player") or body is CharacterBody2D) and not overlapping_player_bodies.has(body):
		overlapping_player_bodies.append(body)
		emit_signal("occupancy_changed", true, overlapping_player_bodies.size())
		print("[LIGHT_BRIDGE %s] Player entered bridge zone: %s (Occupants: %d)" % [bridge_id, body.name, overlapping_player_bodies.size()])


func _on_area_body_exited(body: Node2D) -> void:
	if overlapping_player_bodies.has(body):
		overlapping_player_bodies.erase(body)
		var still_occupied = is_occupied()
		emit_signal("occupancy_changed", still_occupied, overlapping_player_bodies.size())
		print("[LIGHT_BRIDGE %s] Player exited bridge zone: %s (Remaining: %d)" % [bridge_id, body.name, overlapping_player_bodies.size()])

		# If an OPEN authorization was held waiting for zone clearance under active P_INT jurisdiction, finalize now
		if not still_occupied and pending_evidence_for_clearance.size() > 0 and hold_jurisdiction == "P_INT" and not is_hold_deadline_forfeited:
			print("[LIGHT_BRIDGE %s] Zone cleared. Finalizing pending OPEN authorization..." % bridge_id)
			var ev_data = pending_evidence_for_clearance.duplicate(true)
			pending_evidence_for_clearance.clear()
			_apply_open_state(ev_data)


# ------------------------------------------------------------------------------
# STATE MACHINE GATING LOGIC
# ------------------------------------------------------------------------------

func set_to_hold(proposal_id: String, rationale: String = "") -> Variant:
	var clean_rationale = rationale.strip_edges()
	if clean_rationale == "":
		modeled_voltage = 0.00
		modeled_voltage_verified = 0.00
		hold_jurisdiction = "P_EXT"
		if collision_shape:
			collision_shape.set_deferred("disabled", true)
		_append_witness_record("REJECTED_SILENT_HOLD", {
			"proposal_id": proposal_id,
			"delta_k": "EMPTY",
			"hold_jurisdiction": hold_jurisdiction,
			"modeled_voltage": "0.00 V — MODELED SOFTWARE STATE",
			"modeled_voltage_verified": "0.00 V — VERIFIED DE-ENERGIZED READBACK",
			"collision_enabled": false,
			"state": "HOLD_BLUEPRINT"
		})
		printerr("[LIGHT_BRIDGE %s] ERROR: Silent HOLD forbidden! Empty rationale (delta_k = EMPTY) rejected." % bridge_id)
		return false

	var old_state = current_state
	current_state = BridgeState.HOLD_BLUEPRINT
	modeled_voltage = 0.00
	modeled_voltage_verified = 0.00
	pulse_timer = 0.0
	hold_elapsed_time = 0.0
	hold_jurisdiction = "P_INT"
	active_hold_delta_k = clean_rationale
	is_hold_deadline_forfeited = false

	# Strict Fail-Closed Invariant: Collision is disabled in HOLD
	if collision_shape:
		collision_shape.set_deferred("disabled", true)

	var record = _append_witness_record("SET_TO_HOLD", {
		"proposal_id": proposal_id,
		"rationale": clean_rationale,
		"delta_k": clean_rationale,
		"hold_jurisdiction": hold_jurisdiction,
		"modeled_voltage": "0.00 V — MODELED SOFTWARE STATE",
		"modeled_voltage_verified": "0.00 V — VERIFIED DE-ENERGIZED READBACK",
		"collision_enabled": false,
		"state": "HOLD_BLUEPRINT"
	})

	emit_signal("state_transitioned", old_state, current_state, record)
	print("[LIGHT_BRIDGE %s] State -> HOLD_BLUEPRINT (Collision Disabled, 0.00 V Modeled, Event: %s)" % [bridge_id, record["event_id"]])
	return record


func advance_hold_clock(delta_tau: float) -> Dictionary:
	if delta_tau < 0.0:
		printerr("[LIGHT_BRIDGE %s] ERROR: Non-monotone clock rollback rejected (%.3f)." % [bridge_id, delta_tau])
		return {
			"status": "REJECTED_CLOCK_ROLLBACK",
			"success": false,
			"hold_jurisdiction": hold_jurisdiction,
			"open_authorized": false
		}

	if current_state != BridgeState.HOLD_BLUEPRINT:
		return {
			"status": "NOT_IN_HOLD",
			"success": false,
			"hold_jurisdiction": hold_jurisdiction,
			"open_authorized": (current_state == BridgeState.OPEN_REALIZED)
		}

	# First Clock Law: Time passing never mutates HOLD -> OPEN
	hold_elapsed_time += delta_tau
	modeled_voltage = 0.00
	modeled_voltage_verified = 0.00

	# Second Clock Law: Stalling past hold_tau_max forfeits P_INT -> P_EXT and purges pending warrant
	if hold_tau_max > 0.0 and hold_elapsed_time > hold_tau_max and hold_jurisdiction == "P_INT" and not is_hold_deadline_forfeited:
		var had_pending_clearance = pending_evidence_for_clearance.size() > 0
		pending_evidence_for_clearance.clear()
		hold_jurisdiction = "P_EXT"
		is_hold_deadline_forfeited = true
		var forfeit_record = _append_witness_record("HOLD_DEADLINE_FORFEITED", {
			"delta_k": active_hold_delta_k,
			"elapsed_tau": hold_elapsed_time,
			"hold_tau_max": hold_tau_max,
			"previous_jurisdiction": "P_INT",
			"hold_jurisdiction": "P_EXT",
			"pending_clearance_stalled": had_pending_clearance,
			"pending_evidence_purged": had_pending_clearance,
			"open_authorized": false,
			"modeled_voltage": "0.00 V — MODELED SOFTWARE STATE",
			"modeled_voltage_verified": "0.00 V — VERIFIED DE-ENERGIZED READBACK",
			"collision_enabled": false,
			"state": "HOLD_BLUEPRINT"
		})
		emit_signal("hold_jurisdiction_escalated", hold_jurisdiction, hold_elapsed_time, forfeit_record)
		print("[LIGHT_BRIDGE %s] HOLD_DEADLINE_FORFEITED: Elapsed %.3f > %.3f. Jurisdiction P_INT -> P_EXT (0.00 V HOLD preserved)." % [bridge_id, hold_elapsed_time, hold_tau_max])
		return {
			"status": "HOLD_DEADLINE_FORFEITED",
			"success": true,
			"hold_jurisdiction": hold_jurisdiction,
			"elapsed_tau": hold_elapsed_time,
			"open_authorized": false,
			"witness_record": forfeit_record
		}

	return {
		"status": "HOLD_ACTIVE",
		"success": true,
		"hold_jurisdiction": hold_jurisdiction,
		"elapsed_tau": hold_elapsed_time,
		"open_authorized": false
	}


func audit_gate_neutrality(omega_a: String, omega_b: String) -> Dictionary:
	var rule_a = omega_a.strip_edges().to_upper()
	var rule_b = omega_b.strip_edges().to_upper()
	if rule_a == "" or rule_b == "" or rule_a != rule_b:
		var kill_rec = trigger_kill("KILL_GATE_CAPTURE")
		return {
			"neutral": false,
			"status": "KILL_GATE_CAPTURE",
			"omega_a": rule_a,
			"omega_b": rule_b,
			"witness_record": kill_rec
		}

	return {
		"neutral": true,
		"status": "VALID_NEUTRAL_GATE",
		"omega_a": rule_a,
		"omega_b": rule_b
	}


func attempt_open(evidence_payload: Dictionary) -> Dictionary:
	var evidence_id = evidence_payload.get("evidence_id", "")
	if evidence_id.strip_edges() == "":
		print("[LIGHT_BRIDGE %s] ERROR: Cannot OPEN without valid evidence_id!" % bridge_id)
		return {"status": "REJECTED_MISSING_EVIDENCE", "success": false}

	# Invariant: Sticky DK-Latch. KILL state cannot be overridden by new proposals without explicit reset
	if is_kill_latched or current_state == BridgeState.KILL_ABORTED:
		print("[LIGHT_BRIDGE %s] REJECTED: Gate is in KILL_ABORTED (Sticky DK-Latch tripped). Requires explicit reset!" % bridge_id)
		return {
			"status": "REJECTED_LATCHED_KILL",
			"state": "KILL_ABORTED",
			"success": false,
			"evidence_id": evidence_id
		}

	# Idempotency Invariant: If already OPEN, ignore redundant authorization without mutating state or ledger
	if current_state == BridgeState.OPEN_REALIZED:
		print("[LIGHT_BRIDGE %s] IDEMPOTENT: Already in OPEN_REALIZED state. Duplicate request ignored." % bridge_id)
		return {
			"status": "ALREADY_OPEN",
			"state": "OPEN_REALIZED",
			"success": true,
			"evidence_id": active_evidence_id
		}

	# Invariant 4: Occupancy Clearance Gating (SAFETY PATH > DATA PATH)
	if is_occupied():
		pending_evidence_for_clearance = evidence_payload
		active_hold_delta_k = "ZONE_OCCUPIED_BY_PLAYER"
		hold_elapsed_time = 0.0
		hold_jurisdiction = "P_INT"
		is_hold_deadline_forfeited = false
		emit_signal("open_deferred_due_to_occupancy", evidence_id, "ZONE_OCCUPIED_BY_PLAYER")
		print("[LIGHT_BRIDGE %s] GATING: Player in bridge zone! State remains HOLD until clearance." % bridge_id)
		return {
			"status": "DEFERRED_ZONE_OCCUPIED",
			"state": "HOLD_BLUEPRINT",
			"success": false,
			"evidence_id": evidence_id
		}

	return _apply_open_state(evidence_payload)


func _apply_open_state(evidence_payload: Dictionary) -> Dictionary:
	var old_state = current_state
	current_state = BridgeState.OPEN_REALIZED
	modeled_voltage = 5.00
	modeled_voltage_verified = 5.00
	pulse_timer = 0.0
	hold_elapsed_time = 0.0
	is_hold_deadline_forfeited = false
	active_evidence_id = evidence_payload.get("evidence_id", "EV_DEFAULT")

	# Safe Deferred Collision Activation
	if collision_shape:
		collision_shape.set_deferred("disabled", false)

	var record = _append_witness_record("AUTHORIZE_OPEN", {
		"evidence_id": active_evidence_id,
		"evidence_payload": evidence_payload,
		"modeled_voltage": "5.00 V — MODELED SOFTWARE STATE",
		"modeled_voltage_verified": "5.00 V — VERIFIED ENERGIZED READBACK",
		"collision_enabled": true,
		"state": "OPEN_REALIZED"
	})

	emit_signal("state_transitioned", old_state, current_state, record)
	print("[LIGHT_BRIDGE %s] State -> OPEN_REALIZED (Collision Enabled via set_deferred, 5.00 V Modeled, Hash: %s)" % [bridge_id, record["event_hash"]])
	return {
		"status": "AUTHORIZED_OPEN",
		"state": "OPEN_REALIZED",
		"success": true,
		"witness_record": record
	}


func trigger_kill(reason: String = "EMERGENCY_FAIL_CLOSED") -> Dictionary:
	var old_state = current_state
	current_state = BridgeState.KILL_ABORTED
	is_kill_latched = true
	modeled_voltage = 0.00
	modeled_voltage_verified = 0.00
	pulse_timer = 0.0
	hold_elapsed_time = 0.0
	pending_evidence_for_clearance.clear()  # Cancels pending authorization

	# Immediate Fail-Closed Guillotine: Collision disabled
	if collision_shape:
		collision_shape.set_deferred("disabled", true)

	var record = _append_witness_record("KILL_COLLAPSE", {
		"reason": reason,
		"modeled_voltage": "0.00 V — MODELED SOFTWARE STATE",
		"modeled_voltage_verified": "0.00 V — VERIFIED DE-ENERGIZED READBACK",
		"is_kill_latched": true,
		"collision_enabled": false,
		"state": "KILL_ABORTED"
	})

	emit_signal("state_transitioned", old_state, current_state, record)
	print("[LIGHT_BRIDGE %s] State -> KILL_ABORTED (0.00 V Modeled Guillotine Tripped, Reason: %s)" % [bridge_id, reason])
	return record


func reset_bridge(reason: String = "USER_CANVAS_RESET") -> Dictionary:
	# RESET appends a record without erasing the append-only ledger history
	var clean_reason = reason.strip_edges()
	if clean_reason == "":
		clean_reason = "USER_CANVAS_RESET"
	is_kill_latched = false
	pending_evidence_for_clearance.clear()
	var record = _append_witness_record("RESET_CANVAS", {
		"reason": clean_reason,
		"modeled_voltage": "0.00 V — MODELED SOFTWARE STATE",
		"modeled_voltage_verified": "0.00 V — VERIFIED DE-ENERGIZED READBACK",
		"is_kill_latched": false,
		"state": "HOLD_BLUEPRINT"
	})

	set_to_hold("RESET_PROPOSAL_" + str(Time.get_ticks_msec()), clean_reason)
	return record


# ------------------------------------------------------------------------------
# DETERMINISTIC WITNESS LOGGING
# ------------------------------------------------------------------------------
func verify_witness_chain() -> bool:
	var expected_prev = "0000000000000000000000000000000000000000000000000000000000000000"
	for idx in range(witness_history.size()):
		var entry = witness_history[idx]
		if entry.get("sequence_number", -1) != idx:
			return false
		if entry.get("previous_hash", "") != expected_prev:
			return false
		var check_record = {
			"event_id": entry["event_id"],
			"sequence_number": entry["sequence_number"],
			"previous_hash": entry["previous_hash"],
			"bridge_id": entry["bridge_id"],
			"action_type": entry["action_type"],
			"timestamp": entry["timestamp"],
			"details": entry["details"],
			"system_disclaimer": entry["system_disclaimer"]
		}
		var raw_str = JSON.stringify(check_record)
		var ctx = HashingContext.new()
		ctx.start(HashingContext.HASH_SHA256)
		ctx.update(raw_str.to_utf8_buffer())
		var recomputed_hash = ctx.finish().hex_encode()
		if recomputed_hash != entry.get("event_hash", ""):
			return false
		expected_prev = recomputed_hash
	return expected_prev == last_event_hash


func _append_witness_record(action_type: String, details: Dictionary) -> Dictionary:
	var seq_num = witness_history.size()
	var event_id = "EVT_" + str(seq_num + 1).pad_zeros(5)
	var timestamp = Time.get_datetime_string_from_system(true)

	var record = {
		"event_id": event_id,
		"sequence_number": seq_num,
		"previous_hash": last_event_hash,
		"bridge_id": bridge_id,
		"action_type": action_type,
		"timestamp": timestamp,
		"details": details,
		"system_disclaimer": "MODELED_SOFTWARE_STATE_NOT_PHYSICAL_WORM"
	}

	var raw_str = JSON.stringify(record)
	var ctx = HashingContext.new()
	ctx.start(HashingContext.HASH_SHA256)
	ctx.update(raw_str.to_utf8_buffer())
	var computed_hash = ctx.finish().hex_encode()

	record["event_hash"] = computed_hash
	last_event_hash = computed_hash
	last_event_id = event_id

	witness_history.append(record)
	return record
