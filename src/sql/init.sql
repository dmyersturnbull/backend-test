CREATE TABLE IF NOT EXISTS user_metrics (
  user_id INT NOT NULL,
  user_name varchar(250) NOT NULL,
  n_experiments int NOT NULL,
  top_compound varchar(250) NOT NULL,
  mean_experiment_run_time float NOT NULL,
  PRIMARY KEY (user_id)
);
