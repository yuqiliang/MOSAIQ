from scripts.run_tabular_baselines import make_estimator


def test_parallel_estimators_default_to_one_worker() -> None:
    for model in ["elastic_net_cv", "random_forest", "xgboost"]:
        estimator = make_estimator(model, {}, seed=2026)
        assert estimator.n_jobs == 1


def test_parallel_estimator_worker_count_can_be_overridden() -> None:
    estimator = make_estimator("random_forest", {"n_jobs": 2}, seed=2026)
    assert estimator.n_jobs == 2
