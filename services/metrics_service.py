import pandas as pd


ROOT_CAUSE_CATEGORIES = ["Code", "Stored Proc", "UI", "Environment", "Configuration", "Database"]
STATUS_CATEGORIES = ["Open", "Fixed, in Retest", "Closed/Deferred"]


def _numeric(series_or_value):
    return pd.to_numeric(series_or_value, errors='coerce').fillna(0)


def _pct(values, denominator):
    values = _numeric(values)
    denom = _numeric(denominator).replace(0, pd.NA)
    return (values / denom * 100).fillna(0).round(4)


def build_execution_data(data):
    """Build normalized execution metrics by cycle from metrics.db tables."""
    source = data.get('test_execution', pd.DataFrame()).copy()
    if source.empty:
        return pd.DataFrame(
            columns=[
                'cycle_name',
                'planned_test_cases',
                'executed_test_cases',
                'passed_test_cases',
                'failed_test_cases',
                'blocked_test_cases',
                'deferred_test_cases',
                'execution_pct',
                'pass_rate_pct',
            ]
        )

    execution = pd.DataFrame()
    execution['cycle_name'] = source.get('environment', pd.Series(dtype='object')).astype(str)
    execution['planned_test_cases'] = _numeric(source.get('planned_test_cases', 0)).astype(int)
    execution['executed_test_cases'] = _numeric(source.get('total_executed_test_cases', 0)).astype(int)
    execution['passed_test_cases'] = _numeric(source.get('total_passed_test_cases', 0)).astype(int)
    execution['failed_test_cases'] = _numeric(source.get('total_failed_test_cases', 0)).astype(int)
    execution['blocked_test_cases'] = _numeric(source.get('blocked_test_cases', 0)).astype(int)
    execution['deferred_test_cases'] = _numeric(source.get('deferred_test_cases', 0)).astype(int)
    execution['execution_pct'] = _pct(execution['executed_test_cases'], execution['planned_test_cases'])
    execution['pass_rate_pct'] = _pct(execution['passed_test_cases'], execution['executed_test_cases'])
    return execution

def calculate_kpis(data):
    """Calculate KPIs from test_execution and defects tables."""
    kpis = {}

    test_execution_table = data.get('test_execution')
    defects_table = data.get('defects')

    # Calculate KPIs from test_execution table
    if test_execution_table is not None and len(test_execution_table) > 0:
        # Total test cases across all cycles
        kpis['total_test_cases'] = int(_numeric(test_execution_table['planned_test_cases']).sum())
        
        # Executed test cases across all cycles
        kpis['executed_test_cases'] = int(_numeric(test_execution_table['total_executed_test_cases']).sum())
        
        # Total passed test cases
        total_passed = int(_numeric(test_execution_table['total_passed_test_cases']).sum())
        
        # Pass rate: (total_passed / total_executed) * 100
        if kpis['executed_test_cases'] > 0:
            kpis['pass_rate_pct'] = (total_passed / kpis['executed_test_cases']) * 100
        else:
            kpis['pass_rate_pct'] = 0.0

        # Execution rate: (total_executed / total_test_cases) * 100
        if kpis['total_test_cases'] > 0:
            kpis['execution_rate_pct'] = (kpis['executed_test_cases'] / kpis['total_test_cases']) * 100
        else:
            kpis['execution_rate_pct'] = 0.0

        # Deferred tests
        kpis['deferred_tests'] = int(
            _numeric(test_execution_table['deferred_test_cases']).sum()
        )
        
        # Scope coverage: average of scope_executed_pct across cycles
        scope_pcts = pd.to_numeric(
            test_execution_table['scope_executed_pct'].astype(str).str.rstrip('%'), 
            errors='coerce'
        )
        kpis['scope_coverage_pct'] = float(scope_pcts.mean()) if not scope_pcts.dropna().empty else 0.0
    else:
        kpis['total_test_cases'] = 0
        kpis['executed_test_cases'] = 0
        kpis['pass_rate_pct'] = 0.0
        kpis['execution_rate_pct'] = 0.0
        kpis['deferred_tests'] = 0
        kpis['scope_coverage_pct'] = 0.0

    # Calculate KPIs from defects table
    if defects_table is not None and len(defects_table) > 0:
        # Total defects
        kpis['total_defects'] = int(len(defects_table))
        
        closed_count = defects_table[
            defects_table['status'].astype(str).str.strip().eq('Closed/Deferred')
        ].shape[0]
        kpis['closed_defects'] = int(closed_count)
        
        # Severity breakdown
        severity_counts = defects_table['severity'].astype(str).str.lower().value_counts()
        kpis['critical_defects'] = int(severity_counts.get('critical', 0))
        kpis['high_defects'] = int(severity_counts.get('high', 0))
        kpis['medium_defects'] = int(severity_counts.get('medium', 0))
        kpis['low_defects'] = int(severity_counts.get('low', 0))
    else:
        kpis['total_defects'] = 0
        kpis['closed_defects'] = 0
        kpis['critical_defects'] = 0
        kpis['high_defects'] = 0
        kpis['medium_defects'] = 0
        kpis['low_defects'] = 0

    # Error discovery rate: (total_defects / total_executed) * 100
    if kpis['executed_test_cases'] > 0:
        kpis['error_discovery_rate_pct'] = (kpis['total_defects'] / kpis['executed_test_cases']) * 100
    else:
        kpis['error_discovery_rate_pct'] = 0.0

    return kpis


def get_analytics_datasets(data):
    """Generate analytics datasets from defects table."""
    datasets = {}

    defect_table = data.get('defects')
    execution_table = build_execution_data(data)

    if not execution_table.empty:
        datasets['test_execution_by_cycle'] = execution_table

    if defect_table is not None and len(defect_table) > 0:
        # Defects by severity
        severity_counts = defect_table['severity'].value_counts().reset_index()
        severity_counts.columns = ['severity', 'count']
        datasets['defects_by_severity'] = severity_counts

        # Defects by cycle
        cycle_counts = defect_table['cycle_name'].value_counts().reset_index()
        cycle_counts.columns = ['cycle_name', 'count']
        datasets['defects_by_cycle'] = cycle_counts

        # Defects by root cause
        if 'root_cause' in defect_table.columns:
            root_cause_counts = (
                defect_table['root_cause']
                .value_counts()
                .reindex(ROOT_CAUSE_CATEGORIES, fill_value=0)
                .reset_index()
            )
            root_cause_counts.columns = ['root_cause', 'count']
            datasets['defects_by_root_cause'] = root_cause_counts

        # Defect status distribution
        status_counts = (
            defect_table['status']
            .value_counts()
            .reindex(STATUS_CATEGORIES, fill_value=0)
            .reset_index()
        )
        status_counts.columns = ['status', 'count']
        datasets['defect_status_distribution'] = status_counts

        # Defects by severity and cycle (cross-tabulation)
        defects_per_cycle = defect_table.groupby(['cycle_name', 'severity']).size().reset_index(name='count')
        datasets['defects_per_cycle'] = defects_per_cycle

        # Defects by severity and status (for stacked bar chart)
        status_severity = defect_table.groupby(['status', 'severity']).size().reset_index(name='count')
        datasets['defects_by_status_priority'] = status_severity

        # Weekly defect trend
        if 'discovered_week' in defect_table.columns:
            weekly_counts = defect_table['discovered_week'].value_counts().reset_index()
            weekly_counts.columns = ['week', 'count']
            datasets['weekly_defect_trend'] = weekly_counts.sort_values('week')

    return datasets



    
