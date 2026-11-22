"""Shared test policy. Offline guards this process, not arbitrary isolated children."""
from __future__ import annotations

import ast
import importlib.abc
import os
from pathlib import Path
import sys

import pytest

# Explicit boundaries keep pure tests in mixed files and historical snapshots intact.
LIVE_TESTS: set[str] = set("""
test_bezier_local_physics.py::test_actual_bezier_native_guard_counts_attempt_and_stops
test_bezier_local_physics.py::test_native_coast_failure_preserves_completed_bezier_cutoff
test_bezier_local_physics.py::test_native_nonzero_curvature_independent_variable_mass_integral
test_bezier_local_physics.py::test_native_zero_curvature_embeds_old_nonzero_linear_guidance
test_bezier_local_targeting.py::test_runner_provenance_and_counts_with_pure_injected_campaign
test_bounded_local_targeting.py::test_actual_native_deadline_wrapping_retains_budget_classification
test_bounded_local_targeting.py::test_new_budget_native_adapter_matches_frozen_d15
test_bounded_local_targeting.py::test_runner_provenance_with_injected_no_native_study
test_cli.py::test_ephemeris_validates_first_and_emits_manifest
test_cli.py::test_human_ephemeris_labels_units_and_frame
test_cli.py::test_real_ephemeris_subprocess_is_reproducible
test_coast_diagnostic.py::test_native_coast_matches_uniform_motion
test_coast_step_study.py::test_profiles_change_only_cap_and_reach_native_factory
test_environment.py::test_d16_scipy_pin_matches_conda_without_changing_historical_dependencies
test_ephemeris.py::test_real_tudatpy_parity_and_round_trip
test_explorer.py::test_reference_arc_endpoints_repeatability_and_errors
test_explorer.py::test_sampler_matches_independent_circular_orbit
test_explorer_ui.py::test_elapsed_days_reset_on_candidate_change
test_explorer_ui.py::test_example_search_slider_edit_and_invalid_rerun
test_explorer_ui.py::test_failure_clears_successful_provenance
test_explorer_ui.py::test_preferences_filter_help_and_budget
test_explorer_ui.py::test_provenance_lifecycle_and_no_repeated_work
test_explorer_ui.py::test_provenance_matches_cli_and_detaches_inputs
test_explorer_ui.py::test_sampling_failure_removes_result
test_explorer_ui.py::test_search_failure_clears_previous_result
test_local_burn.py::test_actual_derivative_stage_impact_guard
test_local_burn.py::test_agreement_accepts_threshold_equality
test_local_burn.py::test_agreement_threshold_failures
test_local_burn.py::test_coast_mass_change_is_rejected
test_local_burn.py::test_failure_stops_without_retry
test_local_burn.py::test_frozen_profiles_handoff_and_separate_miss
test_local_burn.py::test_guard_failure_after_preparation_stops_schedule
test_local_burn.py::test_native_callback_enforces_shared_deadline
test_local_burn.py::test_native_circular_orbit_oracle
test_local_burn.py::test_native_failure_history_guards
test_local_burn.py::test_native_thrust_mass_oracle_and_exact_handoff
test_local_targeting.py::test_actual_steered_native_stage_guards
test_local_targeting.py::test_native_coast_failure_retains_completed_cutoff
test_local_targeting.py::test_native_invalid_guidance_stops_counted_launch
test_local_targeting.py::test_native_smooth_thrust_independent_gaussian_integral
test_local_targeting.py::test_runner_records_current_and_historical_provenance_without_live_study
test_local_targeting.py::test_zero_steering_native_equals_unchanged_d14
test_m3_fixture.py::test_provisional_fixture_changes_budget_flag_not_candidate_physics
test_native_adaptive_safety.py::test_bounded_subdivision_with_known_relative_acceleration
test_native_arc_handoff.py::test_three_native_arcs_preserve_state_and_mass_handoff
test_native_burn.py::test_native_engine_couples_translation_and_mass
test_native_minimum_step.py::test_native_minimum_step_failure_rejects_partial_result
test_native_safety_sampling.py::test_native_distance_event_localization_requires_detection
test_native_safety_sampling.py::test_native_full_step_guard_can_miss_an_internal_crossing
test_r5_short_coast_inputs.py::test_actual_module_version_mismatch
test_r5_short_coast_inputs.py::test_actual_runtime_identity_is_stable_and_extended
test_r5_short_coast_inputs.py::test_extra_source_and_outside_checkout_rejection
test_r5_short_coast_inputs.py::test_live_coefficient_change_changes_snapshot
test_r5_short_coast_inputs.py::test_solver_or_build_drift_rejected
test_r5_short_coast_native.py::test_actual_spice_environment_at_time_zero
test_r5_short_coast_native.py::test_coarse_epoch_rejected_before_propagation
test_r5_short_coast_native.py::test_fifth_attempt_stops_before_native_call
test_r5_short_coast_native.py::test_invalid_source_gm
test_r5_short_coast_native.py::test_inventory_ignores_map_order_but_rejects_extras_and_gm_drift
test_r5_short_coast_native.py::test_native_circular_orbit_against_closed_form
test_r5_short_coast_native.py::test_native_direct_ssb_sources_against_decimal80
test_r5_short_coast_native.py::test_native_error_counts_attempt_without_return
test_r5_short_coast_native.py::test_profile_and_sample_rejection
test_r5_short_coast_native.py::test_returned_history_survives_deadline
test_r5_short_coast_native.py::test_source_construction_and_inventory_errors
test_r5_short_coast_native.py::test_synthetic_zero_force_exact_line
test_r5_short_coast_oracle.py::test_spice_boundary_passes_exact_epoch_and_si
test_r5_short_coast_oracle.py::test_spice_boundary_translates_actual_library_error
test_r5_short_coast_oracle.py::test_spice_provider_matches_actual_tudat_boundary
test_r5_short_coast_oracle.py::test_spice_si_conversion_rejects_overflow
test_reference_plan.py::test_full_reference_plan_matches_pinned_scientific_baseline
test_research_export.py::test_late_result_is_not_published
test_research_export.py::test_other_stale_identity_invalidates_downloads
test_research_export.py::test_search_error_retains_available_diagnostics
test_research_export.py::test_ui_exchange_failure_retains_diagnostics_without_download
test_research_export.py::test_ui_positive_export_stale_inputs_candidate_and_sort
test_research_export.py::test_ui_resource_change_invalidates_downloads
test_research_export.py::test_unqualified_coast_is_never_promoted
test_research_propagation.py::test_native_three_arc_composition_matches_rocket_equation
test_trajectory_arc_completion.py::test_native_time_rejects_mismatch_hidden_by_float_epoch
test_trajectory_collision.py::test_real_environment_uses_exact_pinned_collision_surfaces
test_trajectory_conservation.py::test_ten_orbit_point_mass_conservation
test_trajectory_environment.py::test_altered_harmonic_resource_reports_expected_and_actual_hash
test_trajectory_environment.py::test_coverage_failure_precedes_body_system_creation
test_trajectory_environment.py::test_direct_coverage_invalid_epochs_precede_native_inspection
test_trajectory_environment.py::test_direct_coverage_rejects_invalid_chains
test_trajectory_environment.py::test_direct_settings_reject_wrong_model_frame_or_aberration
test_trajectory_environment.py::test_drifted_moon_harmonic_settings_are_rejected
test_trajectory_environment.py::test_environment_stage_expiry_discards_result_without_resetting_budget
test_trajectory_environment.py::test_missing_harmonic_resource_is_chained_without_fallback
test_trajectory_environment.py::test_missing_standard_kernel_is_chained_before_environment_creation
test_trajectory_environment.py::test_production_direct_ephemerides_match_candidate_and_saturn_joins
test_trajectory_environment.py::test_real_environment_uses_exact_direct_resources_and_frames
test_trajectory_environment.py::test_uncovered_spice_interval_is_chained_without_unlimited_fallback
test_trajectory_ephemeris.py::test_full_candidate_interpolation_against_direct_spice
test_trajectory_ephemeris.py::test_moving_body_chord_deviation_is_not_interpolation_error
test_trajectory_ephemeris.py::test_native_arithmetic_binary_matches_static_observation
test_trajectory_ephemeris.py::test_native_ephemeris_grid_switch_does_not_guarantee_smooth_position
test_trajectory_ephemeris.py::test_native_queries_preserve_sampled_fpcr
test_trajectory_ephemeris.py::test_native_six_node_amplification_matches_exact_control
test_trajectory_ephemeris.py::test_pinned_grid_binary64_arithmetic_matches_exact_rationals
test_trajectory_fourth_curvature.py::test_fourth_endpoint_conditional_monopole_curvature
test_trajectory_fourth_inputs.py::test_fourth_harmonic_binary64_input_binding
test_trajectory_gravity.py::test_full_force_coupled_burn_preserves_constant_mass_flow
test_trajectory_gravity.py::test_gravity_factory_failure_is_chained_with_candidate_context
test_trajectory_gravity.py::test_gravity_settings_have_exact_sources_types_and_order
test_trajectory_gravity.py::test_real_gravity_matches_independent_fixed_state_component_sum
test_trajectory_gravity_bound.py::test_pinned_harmonic_surface_bounds_are_finite_and_decrease_with_distance
test_trajectory_guidance.py::test_tnw_basis_matches_direct_tudat_rotation
test_trajectory_handoff.py::test_boundary_body_and_ephemeris_failures_are_contextual_and_chained
test_trajectory_handoff.py::test_boundary_states_match_direct_tudatpy_and_spice_conversion
test_trajectory_handoff.py::test_circular_departure_preserves_argument_of_latitude_equivalence
test_trajectory_handoff.py::test_reference_boundary_radii_are_body_relative_and_distinct
test_trajectory_harmonic_profile.py::test_stored_mars_harmonic_profile
test_trajectory_integrator.py::test_native_integrator_receives_exact_settings
test_trajectory_radiation.py::test_clear_solar_radiation_scales_with_area_coefficient_and_current_mass
test_trajectory_radiation.py::test_clear_umbra_and_penumbra_match_direct_tudat_shadow_function
test_trajectory_radiation.py::test_radiation_factory_failure_is_chained_with_candidate_context
test_trajectory_radiation.py::test_radiation_target_install_failure_is_chained
test_trajectory_radiation.py::test_real_environment_installs_exact_explicit_solar_radiation_setup
test_trajectory_relativity.py::test_ppn_parameter_failure_is_chained_with_candidate_context
test_trajectory_relativity.py::test_real_environment_installs_exact_sun_schwarzschild_correction
test_trajectory_relativity.py::test_real_schwarzschild_acceleration_matches_independent_formula
test_trajectory_relativity.py::test_relativity_factory_failure_is_chained_with_candidate_context
test_trajectory_spk.py::test_direct_and_tabulated_ephemeris_lookup_cost
test_trajectory_spk.py::test_direct_spice_errors_do_not_poison_valid_queries
test_trajectory_spk.py::test_loaded_spk_chain_coverage_contains_candidate_interval
test_trajectory_spk.py::test_pck_rotation_rates_reject_changed_source
test_trajectory_spk.py::test_sampled_spk_chains_match_tudat_states
test_trajectory_spk.py::test_saturn_junction_query_order_is_repeatable
test_trajectory_spk.py::test_saturn_source_file_segment_inventory
test_trajectory_spk.py::test_saturn_spk_segment_junction
test_trajectory_spk.py::test_spk_position_replay_distinguishes_fused_rounding
test_trajectory_spk.py::test_type2_velocity_replay_matches_native_single_modes
test_trajectory_spk.py::test_type3_velocity_uses_stored_series_not_position_derivative
test_trajectory_spk.py::test_unknown_spk_body_has_no_descriptor
test_transfer.py::test_all_deferred_scenario_fields_leave_search_science_unchanged
test_transfer.py::test_deadline_never_returns_a_partial_result
test_transfer.py::test_inherited_deadline_is_not_restarted_or_allowed_to_extend_budget
test_transfer.py::test_lambert_wrapper_matches_direct_tudatpy_in_three_dimensions
test_transfer.py::test_patched_conic_matches_energy_equation
test_transfer.py::test_reduced_real_spice_search_is_complete
test_transfer.py::test_rotated_quarter_circle_lambert_matches_analytic_velocity
test_transfer.py::test_search_caches_endpoints_counts_lambert_failures_and_ignores_seed
test_transfer_contracts.py::test_real_exact_tdb_state_and_gm_match_direct_tudatpy
test_transfer_scientific_parity.py::test_one_candidate_matches_direct_pinned_tudatpy_and_spice
test_transfer_scientific_parity.py::test_small_real_search_is_reproducible_and_ignores_deferred_fields
""".split())
ARCHIVE_TESTS: set[str] = {
    "test_split_coast_study.py::test_split_path_replays_archived_bits",
}
_NATIVE = {"tudatpy", "spiceypy"}
_offline_active = False


class _RejectNative(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path: object = None, target: object = None) -> None:
        if _offline_active and fullname.split(".", 1)[0] in _NATIVE:
            pytest.fail("offline test attempted native import: " + fullname, pytrace=False)


_finder = _RejectNative()


def _reject_cspice(event: str, args: tuple[object, ...]) -> None:
    if not _offline_active or event != "ctypes.dlopen" or not args:
        return
    name = args[0]
    if isinstance(name, (str, bytes, os.PathLike)):
        library = os.fsdecode(name).lower()
        if any(package in library for package in (*_NATIVE, "cspice")):
            pytest.fail("offline test attempted native load: " + library, pytrace=False)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--offline", action="store_true", help="exclude live tests and forbid native access in this process")
    parser.addoption("--run-archive", action="store_true", help="enable exact historical-environment checks")


def pytest_configure(config: pytest.Config) -> None:
    global _offline_active
    if config.getoption("--offline"):
        if any(name.split(".", 1)[0] in _NATIVE for name in sys.modules):
            raise pytest.UsageError("offline tests require a fresh process without native bindings")
        _offline_active = True
        sys.meta_path.insert(0, _finder)
        sys.addaudithook(_reject_cspice)


def pytest_unconfigure(config: pytest.Config) -> None:
    global _offline_active
    _offline_active = False
    if _finder in sys.meta_path:
        sys.meta_path.remove(_finder)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    files = {item.path.name: Path(item.path) for item in items}
    declarations: dict[str, set[str]] = {}
    for node in LIVE_TESTS | ARCHIVE_TESTS:
        filename, _, name = node.partition("::")
        if filename not in files:
            continue
        if filename not in declarations:
            tree = ast.parse(files[filename].read_text())
            declarations[filename] = {entry.name for entry in tree.body if isinstance(entry, ast.FunctionDef)}
        if name not in declarations[filename]:
            raise pytest.UsageError("stale live/archive classification: " + node)
    kept, excluded = [], []
    for item in items:
        node = item.path.name + "::" + (getattr(item, "originalname", None) or item.name.split("[", 1)[0])
        if node in LIVE_TESTS:
            item.add_marker(pytest.mark.live)
        if node in ARCHIVE_TESTS:
            item.add_marker(pytest.mark.archive)
        if item.get_closest_marker("archive") and not config.getoption("--run-archive"):
            item.add_marker(pytest.mark.skip(reason="exact historical-environment check; enable with --run-archive"))
        if config.getoption("--offline") and item.get_closest_marker("live"):
            excluded.append(item)
        else:
            kept.append(item)
    if excluded:
        config.hook.pytest_deselected(items=excluded)
        items[:] = kept
