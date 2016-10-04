#!/usr/bin/env python
#
# tournament.py -- implementation of a Swiss-system tournament
#

import psycopg2
import itertools
import pprint
import operator

def connect():
    """Connect to the PostgreSQL database.  Returns a database connection.
    
    Returns: (psycopg2 connection object)
    """
    return psycopg2.connect("dbname=tournament")

def closeConnection(c, cur):
    """Close the passed in connection
    
    Args:
        (psycopg2 connection object) c
        (psycopg2 cursor object) cur
    """
    c.commit()
    cur.close()
    c.close()

def deleteMatches():
    """Removes all the match records from the database."""
    c = connect()
    cur = c.cursor()

    cur.execute("DELETE FROM matchinfo;")
    
    closeConnection(c,cur)

def deletePlayers():
    """
    Removes all the player records from the database
    as well as the tournaments
    """
    c = connect()
    cur = c.cursor()

    cur.execute("DELETE FROM tournaments;")
    cur.execute("DELETE FROM players;")
    
    closeConnection(c,cur)

def countPlayers(tournament_id):
    """Returns the number of players currently registered in the tournament
    
    Args:
      tournament_id: A unique name or ID for the tournament in which the player is playing
    """
    c = connect()
    cur = c.cursor()

    cur.execute("SELECT players.player_id FROM players, tournaments WHERE players.player_id = tournaments.player_id AND tournaments.tournament_id = %s;", (str(tournament_id),))
    count = cur.rowcount
    
    closeConnection(c,cur)
    return count


def registerPlayer(name, tournament_id):
    """Adds a player to the tournament database.

    If a player wants to be in multiple tournaments, they will have to register twice, as if
    they are two different players.
  
    Args:
      name: the player's full name (need not be unique).
      tournament_id: A unique name or ID for the tournament in which the player is playing
    """
    c = connect()
    cur = c.cursor()
    cur.execute("INSERT INTO players (player_name) VALUES (%s) RETURNING player_id;", (name,))
    player_id = cur.fetchone()[0]
    cur.execute("INSERT INTO tournaments (tournament_id, player_id) VALUES (%s, %s);", (tournament_id, player_id))
    
    closeConnection(c,cur)

def playerStandings(tournament_id):
    """Returns a list of the players and their win records, sorted by wins.

    The first entry in the list should be the player in first place, or a player
    tied for first place if there is currently a tie. This list of players is from
    a particular tournament

    Returns:
      A list of tuples, each of which contains (id, name, wins, matches, tournament):
        id: the player's unique id (assigned by the database)
        name: the player's full name (as registered)
        wins: the number of matches the player has won
        matches: the number of matches the player has played
        tournament: the ID of the tournament this player has played
    """
    c = connect()
    cur = c.cursor()

    array = []
    cur.execute("SELECT * FROM view_standings WHERE tournament_id = (%s);", (str(tournament_id),))
    for row in cur:
        array.append(row)
    
    closeConnection(c,cur)
    return array


def reportMatch(winner, loser, status = "none"):
    """Records the outcome of a single match between two players.

    Reports a bye round as a player winning against themselves

    Args:
      winner:  the id number of the player who won
      loser:  the id number of the player who lost
      status: String 'win', 'loose', or 'draw'
    """
    c = connect()
    cur = c.cursor()
    
    if (winner == loser):
        cur.execute("INSERT INTO matchinfo (player_id,played_against,status) VALUES (%s,%s,'win');", (winner,winner))
    elif (status == 'draw'):
        cur.execute("INSERT INTO matchinfo (player_id,played_against,status) VALUES (%s,%s,'draw');", (winner,loser))
        cur.execute("INSERT INTO matchinfo (player_id,played_against,status) VALUES (%s,%s,'draw');", (loser,winner))
    else:
        cur.execute("INSERT INTO matchinfo (player_id,played_against,status) VALUES (%s,%s,'win');", (winner,loser))
        cur.execute("INSERT INTO matchinfo (player_id,played_against,status) VALUES (%s,%s,'loose');", (loser,winner))

    closeConnection(c,cur)

def isRematch(p1id, p2id):
    """
    Given two player ID's as input, checks if the players have played previously
    This works for checking if the player has been given a "bye" round as well!

    Args:
        p1id: ID of player1
        p2id: ID of player2
    """
    c = connect()
    cur = c.cursor()

    cur.execute("SELECT * FROM matchinfo WHERE player_id = %s AND played_against = %s;", (p1id,p2id))
    count = cur.rowcount
    if count == 0:
        return False
    return True

def createDeltas(standings, all_pairings):
    """
    Adds a tuple containing the Delta and OMWdelta to the all_pairings structure.

    Args:
        standings: Same structure as returned from playerStandings
        all_pairings: list of tuples of paired standings (if you take two random standings A and B
                      from the playerStandings() output, put them in a list of tuples like [(A,B),..])
    """
    out_list = []
    for pair in all_pairings:
        delta = abs(pair[0][2] - pair[1][2])
        OMWdelta = abs(getPlayerOMW(standings, pair[0][0]) - getPlayerOMW(standings, pair[1][0]))
        pair = pair + (delta, OMWdelta)
        out_list.append(pair)
    out_list = sortByDeltas(out_list)
    return out_list

def getPlayerScore(standings, playerId):
    """
    Gets the score for a specific player

    Args:
        standings: Same structure as returned from playerStandings
        playerId: The id of the player whos score you wish to get

    Returns:
        int: the score of that player
    """
    for player in standings:
        if(player[0] == playerId):
            return player[2]
    # If player not found Throw exception
    raise Exception("Player was not found")

def getPlayerOMW(standings, playerId):
    """
    Gets the Opponent match wins for the selected player Id
    
    Args:
        standings: A list of tuples structured as returned by playerStandings
        playerId: An int referring to the player whose OMW you want to get

    Returns:
        int: the OMW of the player
    """
    c = connect()
    cur = c.cursor()

    played_against = []
    cur.execute("SELECT played_against FROM matchinfo WHERE player_id = %s;", (playerId,))
    for row in cur:
        played_against.append(row)
    closeConnection(c,cur)
    
    sum_score = 0
    for opponent in played_against:
        sum_score = sum_score + getPlayerScore(standings, playerId)

    return sum_score


def sortByDeltas(all_pairings):
    """
    Sorts the pairing list by the point differences between players (delts points and delta OMW)

    Args:
        all_pairings: A list of tuples of the pairing results.

    Returns:
        list: Sorted list, same structure as input
    """
    out_list = []
    out_list = sorted(all_pairings, key = operator.itemgetter(2, 3))# key=lambda pair: pair[2])
    return out_list

def removePlayerFromPairList(all_pairings, player_id):
    """
    Removes a player from the all_pairings list

    Args:
        all_pairings: A list of tuples of the pairing results.

    Returns:
        list: Same list with all pairings involving that player removed
    """
    out_list = []
    for pair in all_pairings:
        if ((pair[0][0] == player_id) | (pair[1][0] == player_id)):
            pass
        else:
            out_list.append(pair)

    return out_list

def selectByeRound(all_pairings):
    """
    Selects the lowest scoring player eligable to receive a bye round

    Args:
        all_pairings: A list of tuples of the pairing results.

    Returns:
        tuple: A single pairing which is the selected bye round
    """
    bye_list = []
    for pair in all_pairings:
        if (pair[0][0] == pair[1][0]):
            bye_list.append(pair)
    selected_bye = bye_list[-1]
    return selected_bye

def removeAllByeRounds(all_pairings):
    """
    Removes all bye rounds from the all_pairings list

    Args:
        all_pairings: A list of tuples of the pairing results.

    Returns:
        list: Same as input, all bye rounds removed
    """
    out_list = []
    for pair in all_pairings:
        if (pair[0][0] != pair[1][0]):
            out_list.append(pair)
    return out_list

def swissPairings(tournament_id):
    """Returns a list of pairs of players for the next round of a match.
  
    Assuming that there are an even number of players registered, each player
    appears exactly once in the pairings.  Each player is paired with another
    player with an equal or nearly-equal win record, that is, a player adjacent
    to him or her in the standings. If a bye round is returned, it si shown as
    a player match with themselves. Bye round always first in list
  
    Returns:
      A list of tuples, each of which contains (id1, name1, id2, name2)
        id1: the first player's unique id
        name1: the first player's name
        id2: the second player's unique id
        name2: the second player's name
    """
    # all_possible pairings list looks like this
    #[(pID, Pname, Pwind, Pmatches),(P2 same info), delta]
    standings = playerStandings(tournament_id)
    pairingList = []
    all_possible_pairings = []
    # If even number of players
    # sort by number of wins
    if (countPlayers(tournament_id) % 2) == 0:
        for combo in itertools.combinations(standings, 2):
            #Remove any invalid combination
            #remove any repeat matches or already done passes
            if isRematch(combo[0][0], combo[1][0]):
                next
            all_possible_pairings.append(combo)

        all_possible_pairings = createDeltas(standings, all_possible_pairings)
        
        while (len(all_possible_pairings) > 0):
            p1id = all_possible_pairings[0][0][0] 
            p1name = all_possible_pairings[0][0][1]
            p2id = all_possible_pairings[0][1][0]
            p2name = all_possible_pairings[0][1][1]
            pairingList.append((p1id, p1name, p2id, p2name)) 
            all_possible_pairings = removePlayerFromPairList(all_possible_pairings, p1id)
            all_possible_pairings = removePlayerFromPairList(all_possible_pairings, p2id)
        return pairingList

    # If odd number of players
    else:
        for combo in itertools.combinations_with_replacement(standings, 2):
            #Remove any invalid combination
            #remove any repeat matches or already done bye rounds
            if isRematch(combo[0][0], combo[1][0]):
                next
            all_possible_pairings.append(combo)

        all_possible_pairings = createDeltas(standings, all_possible_pairings)
        # selects a random valid bye round
        # removes the rest of them from the list, so that an even
        # number of players should be left
        bye_round = selectByeRound(all_possible_pairings)
        #print("\nThe bye round is:\n")
        #print(bye_round)
        pairingList.append((bye_round[0][0],bye_round[0][1],bye_round[1][0],bye_round[1][1],))
        all_possible_pairings = removePlayerFromPairList(all_possible_pairings, bye_round[0][0])
        all_possible_pairings = removeAllByeRounds(all_possible_pairings)

        while (len(all_possible_pairings) > 0):
            p1id = all_possible_pairings[0][0][0] 
            p1name = all_possible_pairings[0][0][1]
            p2id = all_possible_pairings[0][1][0]
            p2name = all_possible_pairings[0][1][1]
            pairingList.append((p1id, p1name, p2id, p2name)) 
            all_possible_pairings = removePlayerFromPairList(all_possible_pairings, p1id)
            all_possible_pairings = removePlayerFromPairList(all_possible_pairings, p2id)
        #print("\nThe pairing list is:\n")
        #pprint.pprint(pairingList)
        return pairingList
