-- Table definitions for the tournament project.
--
-- Put your SQL 'create table' statements in this file; also 'create view'
-- statements if you choose to use it.
--
-- You can write comments in this file by starting them with two dashes, like
-- these lines here.
-- Connect to fishies first
-- MODIFY THE LINE BELOW TO ANOTHER DATABASE YOU HAVE IN YOUR POSTGRES
\c fishies
drop database tournament;
CREATE DATABASE tournament;
\c tournament
CREATE TABLE players (
	player_id SERIAL PRIMARY KEY,
	player_name TEXT
);
CREATE TABLE matchinfo(
	match_id BIGSERIAL PRIMARY KEY,
	player_id INTEGER references players(player_id),
	played_against INTEGER references players(player_id),
	status TEXT
);
CREATE TABLE tournaments (
	tournament_id TEXT,
	player_id INTEGER references players(player_id)
);

CREATE VIEW view_standings AS
SELECT p.player_id, player_name, SUM(CASE WHEN m.status = 'win' THEN 1 ELSE 0 END) wins, count(m.player_id) total_games, t.tournament_id
FROM players p LEFT JOIN matchinfo m
ON p.player_id = m.player_id JOIN tournaments t ON t.player_id = p.player_id
GROUP BY p.player_id, t.tournament_id
ORDER BY wins DESC;
