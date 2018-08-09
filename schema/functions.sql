
DROP FUNCTION IF EXISTS scheduler.follows_episode(INTEGER,INTEGER);
CREATE OR REPLACE FUNCTION scheduler.follows_episode(_watcherid INTEGER, _episodeid INTEGER) RETURNS BOOLEAN AS $$
DECLARE 
BEGIN
	-- Only care about episodes not marked as watched
	RETURN EXISTS(SELECT * FROM watcher_episode WHERE watched = false AND watcherid = _watcherid AND episodeid = _episodeid);
END;
$$ LANGUAGE 'plpgsql';


DROP FUNCTION IF EXISTS scheduler.follows_tvshow(INTEGER,INTEGER);
CREATE OR REPLACE FUNCTION scheduler.follows_tvshow(_watcherid INTEGER, _tvshowid INTEGER) RETURNS BOOLEAN AS $$
DECLARE 
BEGIN
	RETURN EXISTS(SELECT * FROM watcher_tvshow WHERE watcherid = _watcherid AND tvshowid = _tvshowid);
END;
$$ LANGUAGE 'plpgsql';


DROP FUNCTION IF EXISTS scheduler.add_watcher_tvshow(INTEGER,INTEGER);
CREATE OR REPLACE FUNCTION scheduler.add_watcher_tvshow(_watcherid INTEGER, _tvshowid INTEGER) RETURNS VOID AS $$
DECLARE 
BEGIN
	IF follows_tvshow(_watcherid, _tvshowid) = false THEN
		INSERT INTO watcher_tvshow (watcherid, tvshowid) VALUES (_watcherid, _tvshowid);
	END IF;
	RETURN;
END;
$$ LANGUAGE 'plpgsql';


DROP FUNCTION IF EXISTS scheduler.remove_watcher_tvshow(INTEGER,INTEGER);
CREATE OR REPLACE FUNCTION scheduler.remove_watcher_tvshow(_watcherid INTEGER, _tvshowid INTEGER) RETURNS VOID AS $$
DECLARE 
BEGIN
	DELETE FROM watcher_tvshow WHERE watcherid = _watcherid AND tvshowid = _tvshowid;
	RETURN;
END;
$$ LANGUAGE 'plpgsql';


DROP FUNCTION IF EXISTS scheduler.mark_episode_watched(INTEGER,INTEGER);
CREATE OR REPLACE FUNCTION scheduler.mark_episode_watched(_watcherid INTEGER, _episodeid INTEGER) RETURNS VOID AS $$
DECLARE
BEGIN
	UPDATE watcher_episode SET watched = true WHERE watcherid = _watcherid AND episodeid = _episodeid;
END;
$$ LANGUAGE 'plpgsql';


DROP TRIGGER IF EXISTS episode_populate_watcher_episodes ON scheduler.episode CASCADE;
DROP FUNCTION IF EXISTS scheduler.episode_populate_watcher_episodes();
CREATE OR REPLACE FUNCTION scheduler.episode_populate_watcher_episodes() RETURNS TRIGGER AS $$
DECLARE
	rec RECORD;
BEGIN
	FOR rec in (SELECT * FROM watcher_tvshow WHERE tvshowid = NEW.tvshowid)
	LOOP
		INSERT INTO watcher_episode (episodeid, watcherid) VALUES (NEW.id, rec.watcherid);
	END LOOP;
	RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

CREATE TRIGGER episode_populate_watcher_episodes AFTER INSERT ON scheduler.episode FOR EACH ROW EXECUTE PROCEDURE scheduler.episode_populate_watcher_episodes();


DROP TRIGGER IF EXISTS watcher_tvshow_populate_watcher_episodes ON scheduler.watcher_tvshow CASCADE;
DROP FUNCTION IF EXISTS scheduler.watcher_tvshow_populate_watcher_episodes();
CREATE OR REPLACE FUNCTION scheduler.watcher_tvshow_populate_watcher_episodes() RETURNS TRIGGER AS $$
DECLARE
	rec RECORD;
	in_past BOOLEAN;
BEGIN
	FOR rec IN (SELECT * FROM episode WHERE tvshowid = NEW.tvshowid)
	LOOP
		in_past = rec.airdate < current_date;
		INSERT INTO watcher_episode (episodeid, watcherid, watched) VALUES (rec.id, NEW.watcherid, in_past);
	END LOOP;
	RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

CREATE TRIGGER watcher_tvshow_populate_watcher_episodes AFTER INSERT ON scheduler.watcher_tvshow FOR EACH ROW EXECUTE PROCEDURE scheduler.watcher_tvshow_populate_watcher_episodes();


DROP TRIGGER IF EXISTS watcher_tvshow_remove_watcher_episodes ON scheduler.watcher_tvshow CASCADE;
DROP FUNCTION IF EXISTS scheduler.watcher_tvshow_remove_watcher_episodes();
CREATE OR REPLACE FUNCTION scheduler.watcher_tvshow_remove_watcher_episodes() RETURNS TRIGGER as $$
DECLARE
BEGIN
	DELETE FROM watcher_episode WHERE episodeid IN (SELECT id FROM episode WHERE tvshowid = OLD.tvshowid) AND watcherid = OLD.watcherid;
	RETURN OLD;
END;
$$ LANGUAGE 'plpgsql';

CREATE TRIGGER watcher_tvshow_remove_watcher_episodes AFTER DELETE ON scheduler.watcher_tvshow FOR EACH ROW EXECUTE PROCEDURE scheduler.watcher_tvshow_remove_watcher_episodes();


DROP FUNCTION IF EXISTS scheduler.follows_movie(INTEGER,INTEGER);
CREATE OR REPLACE FUNCTION scheduler.follows_movie(_watcherid INTEGER, _movieid INTEGER) RETURNS BOOLEAN AS $$
DECLARE 
BEGIN
	RETURN EXISTS(SELECT * FROM watcher_movie WHERE watched = false AND watcherid = _watcherid AND movieid = _movieid);
END;
$$ LANGUAGE 'plpgsql';


DROP FUNCTION IF EXISTS scheduler.add_watcher_movie(INTEGER,INTEGER);
CREATE OR REPLACE FUNCTION scheduler.add_watcher_movie(_watcherid INTEGER, _movieid INTEGER) RETURNS VOID AS $$
DECLARE 
BEGIN
	IF follows_movie(_watcherid, _movieid) = false THEN
		INSERT INTO watcher_movie (watcherid, movieid) VALUES (_watcherid, _movieid);
	END IF;
	RETURN;
END;
$$ LANGUAGE 'plpgsql';


DROP FUNCTION IF EXISTS scheduler.remove_watcher_movie(INTEGER,INTEGER);
CREATE OR REPLACE FUNCTION scheduler.remove_watcher_movie(_watcherid INTEGER, _movieid INTEGER) RETURNS VOID AS $$
DECLARE 
BEGIN
	DELETE FROM watcher_movie WHERE watcherid = _watcherid AND movieid = _movieid;
	RETURN;
END;
$$ LANGUAGE 'plpgsql';


DROP FUNCTION IF EXISTS scheduler.mark_movie_watched(INTEGER,INTEGER);
CREATE OR REPLACE FUNCTION scheduler.mark_movie_watched(_watcherid INTEGER, _movieid INTEGER) RETURNS VOID AS $$
DECLARE
BEGIN
	UPDATE watcher_movie SET watched = true WHERE watcherid = _watcherid AND movieid = _movieid;
END;
$$ LANGUAGE 'plpgsql';
