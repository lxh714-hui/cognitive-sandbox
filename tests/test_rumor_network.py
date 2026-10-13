from cognitive_sandbox.information import Clue, InformationPath, Rumor, RumorNetwork


def test_network_tracks_paths_but_character_query_is_holder_scoped():
    network = RumorNetwork()
    clue = Clue("c", "e", "sound", .8, content="异响")
    network.add_clue(clue)
    network.add_rumor(Rumor("r", "c", "liuyiyi", .68, .1, 1, "听说有异响", "resident"))
    network.add_path(InformationPath("c", ("resident", "liuyiyi"), .68, "t1"))
    assert len(network.for_character("liuyiyi")) == 1
    assert network.for_character("resident") == ()
    assert network.snapshot().clues == (clue,)
