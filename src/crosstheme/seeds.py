"""Original, offline starter clues, with independently tuned difficulty levels."""

from crosstheme.engine import Candidate

# answer | easy | medium | hard
SOFTWARE = """
CACHE|Storage for frequently used data|A shortcut to previously fetched data|Where a hit saves a trip
STACK|Last-in, first-out structure|Push-and-pop structure|Structure whose newest arrival leaves first
QUEUE|First-in, first-out structure|Waiting line for jobs|Where cutting in breaks the data structure
ARRAY|Indexed collection of elements|Collection accessed by subscript|A bracket's usual target
HEAP|Structure used for a priority queue|Home of a priority queue's minimum|Where the root may have the lowest priority number
CLASS|Blueprint for objects|Object-oriented blueprint|Source of instances
OBJECT|Instance of a class|Encapsulated state and behavior|A class act's result?
METHOD|Function belonging to a class|Behavior attached to an object|An object's way of doing things
THREAD|Unit of execution within a process|Execution strand|Something a scheduler may spin up
PROCESS|Running instance of a program|Program in execution|An address space's occupant
KERNEL|Core of an operating system|System's privileged core|At the center of a ring-zero operation
LINUX|Operating-system kernel created by Torvalds|Torvalds's kernel|Penguin-powered kernel
PYTHON|Programming language named after a comedy troupe|Language with significant indentation|A language that makes room for meaning?
RUST|Programming language with a borrow checker|Language that checks borrowing|Where lifetimes are a compiler concern
JAVA|Programming language that runs on a virtual machine|Language with a famous virtual machine|Coffee-inspired language
GIT|Distributed version-control tool|Tool for commits and branches|Keeper of a developer's alternate histories?
MERGE|Combine two development branches|Bring branches together|Reconcile divergent histories
COMMIT|Saved change in version control|Repository snapshot|A small piece of recorded history
BRANCH|Separate line of development|Version-control offshoot|A developer's fork in the road?
REBASE|Replay commits on a new base|Move commits to a different starting point|Rewrite a branch's ancestry
DEBUG|Find and fix software errors|Track down a program's faults|Go defect hunting
TEST|Check that software behaves as expected|Assertion-bearing check|Something green may indicate has passed
LOOP|Code that runs repeatedly|Repeated execution construct|It may need a break
RECURSION|A function calling itself|Self-referential technique|A solution that asks a smaller version of itself
RETURN|Send a result back from a function|Hand a value to the caller|A function's parting word
PARSE|Analyze text according to a grammar|Turn tokens into structure|Make grammatical sense of input
TOKEN|Small unit recognized by a compiler|Lexer output|A lexer hands it to a parser
SCHEMA|Structure of a database|Database blueprint|What a migration may reshape
QUERY|Request for data from a database|Database request|A statement seeking a result set
INDEX|Database structure that speeds up lookups|Lookup accelerator|It trades write work for read speed
SERVER|Computer that responds to client requests|Client's counterpart|One that listens on a port
CLIENT|Program that requests a service|Server's counterpart|Requester in a network exchange
SOCKET|Endpoint for network communication|Network endpoint|Where a process meets a connection
PACKET|Unit of data sent over a network|Network delivery unit|A little piece of the traffic
ROUTER|Device that directs network traffic|Packet traffic director|One that knows the next hop
BOOLEAN|Type with true and false values|Two-valued type|Type with no room for maybe
STRING|Sequence of text characters|Text data type|Characters attached?
NULL|Value representing missing data|Absence-of-value marker|A value conspicuous by its absence
MUTEX|Lock allowing one thread at a time|Mutual-exclusion lock|A critical section's bouncer?
ATOMIC|Indivisible, as an operation|All-or-nothing, as an operation|Not to be split by an interleaving
"""
ROMAN = """
CAESAR|Roman leader assassinated on the Ides of March|Victim on the Ides of March|Dictator whose calendar outlasted him
AUGUSTUS|First Roman emperor|Rome's first emperor|Octavian, after 27 B.C.
SENATE|Rome's governing council|Rome's deliberative body|A council with a curia
CONSUL|One of two top elected Roman magistrates|One of a republican pair of chief magistrates|Holder of an annually paired Roman office
TRIBUNE|Roman official who protected plebeians|Plebeian protector|Official with a sacrosanct veto
PRAETOR|Roman magistrate associated with justice|Roman judicial magistrate|Magistrate a step below a consul
LEGION|Large unit of the Roman army|Rome's major military unit|Force with an eagle standard
COHORT|Subdivision of a Roman legion|Legion subdivision|One of ten in a legion
CENTURION|Roman officer who led a century|Roman commander of a century|Officer associated with a vine staff
GLADIUS|Short sword used by Roman soldiers|Legionary's short sword|Blade behind the word "gladiator"
PILUM|Javelin carried by Roman soldiers|Legionary's javelin|A legionary might throw it before closing in
SCUTUM|Large shield carried by Roman soldiers|Legionary's shield|Part of a testudo's roof
FORUM|Public meeting place in a Roman city|Rome's civic heart|Where Roman public life found its square
BASILICA|Roman public hall used for law and business|Roman public hall|Civic building form later used for churches
AQUEDUCT|Structure carrying water to a Roman city|Rome's water carrier|An elevated answer to thirst?
ARCH|Curved structure common in Roman engineering|Keystone-supported span|A keystone keeps it together
DOME|Rounded roof, like the Pantheon's|Pantheon's crowning feature|Roof with an oculus, at the Pantheon
OCULUS|Circular opening in the Pantheon's roof|Pantheon's eye to the sky|An eye that lets the rain in?
TIBER|River flowing through Rome|Rome's river|Waterway beneath the Pons Fabricius
LATIN|Language of ancient Rome|Language of the Caesars|What Cicero spoke
TOGA|Draped garment worn by Roman citizens|Roman citizen's draped attire|A garment with a sinus and an umbo
TUNIC|Basic garment worn under a toga|Garment beneath a toga|Everyday wear beneath ceremonial drapery
DENARIUS|Roman silver coin|Silver coin of Rome|Coin whose name survives in "dinar"
SESTERTIUS|Roman coin worth a quarter of a denarius|Coin worth four asses|Roman unit often used to quote large fortunes
VILLA|Roman country residence|Roman rural estate house|A patrician's country address
ATRIUM|Central hall of a Roman house|Roman home's central hall|Hall with an impluvium
LARES|Roman household guardian gods|Guardians of the Roman home|Deities honored at a lararium
VESTA|Roman goddess of the hearth|Keeper of Rome's sacred hearth|Goddess served by six famous virgins
JANUS|Two-faced Roman god of beginnings|Rome's two-faced god|God looking both ways at a threshold
MARS|Roman god of war|Father of Romulus, in myth|Divine father of Rome's legendary twins
JUNO|Queen of the Roman gods|Jupiter's divine consort|Goddess with a temple on the Capitoline
VENUS|Roman goddess of love|Aeneas's divine mother|Goddess claimed as an ancestor by the Julians
AENEAS|Trojan hero said to be an ancestor of the Romans|Trojan hero of Virgil's epic|Traveler who carried Anchises from Troy
ROMULUS|Legendary founder of Rome|Remus's twin|Founder associated with a fatal boundary dispute
REMUS|Twin brother of Romulus|Romulus's twin|Twin who lost the founding rivalry
PUNIC|Relating to Rome's wars with Carthage|Like three wars with Carthage|Of Rome's great North African rival
HANNIBAL|Carthaginian general who crossed the Alps|Rome's Alpine-crossing foe|Victor at Cannae
RUBICON|River Caesar crossed in defiance of the Senate|Caesar's point-of-no-return river|Boundary crossed in 49 B.C.
OSTIA|Ancient port near Rome|Rome's ancient harbor town|Port at the Tiber's mouth
POMPEII|Roman city buried by Vesuvius|City preserved by volcanic ash|City whose last day came in A.D. 79
"""


def starter_candidates(topic: str, difficulty: str) -> tuple[str, list[Candidate]]:
    lowered = topic.casefold().strip()
    if lowered in ("software engineering", "software", "programming"):
        title, data = "The art of building software", SOFTWARE
    elif lowered in ("roman history", "rome", "ancient rome", "roman"):
        title, data = "All roads lead to Rome", ROMAN
    else:
        raise ValueError(
            "Offline themes: Software engineering or Roman history. Choose Claude or Codex for any other topic."
        )
    index = {"easy": 1, "medium": 2, "hard": 3}[difficulty]
    return title, [
        Candidate(parts[0], parts[index])
        for line in data.strip().splitlines()
        if (parts := line.split("|"))
    ]
