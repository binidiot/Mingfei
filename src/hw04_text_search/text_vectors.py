from nltk import FreqDist, word_tokenize
from collections import defaultdict
import os, math


def dot(dictA, dictB):
    """
     Gibt die Summe der multiplizierten values für die keys der dictionaries aus, aber nur wenn der key in beiden
    dictionaries vorhanden ist

    >>> dot({"001":3, "002":8, "003":2, "004":14}, {"001":8, "002":2, "003":12})
    64
    >>> dot({"first": 0.5, "second": 2.5, "third": 0.05}, {"first": 3, "second": 5})
    14.0
    """
    return sum([dictA.get(tok) * dictB.get(tok, 0) for tok in dictA])


def normalized_tokens(text):
    """ returns a list with lower case tokenized text
    >>> normalized_tokens("Hello World.")
    ['hello', 'world', '.']
    >>> normalized_tokens("This is a Test Sentence")
    ['this', 'is', 'a', 'test', 'sentence']
    """
    return [token.lower() for token in word_tokenize(text)]


class TextDocument:
    def __init__(self, text, id=None):
        """ creates a TextDocument object with variables text, doc id and a frequency list
        """
        self.text = text
        self.token_counts = FreqDist(normalized_tokens(text))
        self.id = id

    @classmethod
    def from_file(cls, filename):
        """ returns a TextDocument object with text read from the file(filename) and filename as the doc id
        """
        with open(filename, 'r') as myfile:
            text = myfile.read()
            while not text[0].isalpha():
                text = text[1:]
            while not text[-1].isalpha():
                text = text[:-1]
        return cls(text, filename)



class DocumentCollection:
    def __init__(self, term_to_df, term_to_docids, docid_to_doc):
        """ creates DocumentCollection object, passes in term_to_df, term_to_docids, docid_to_doc
        """
        # string to int
        self.term_to_df = term_to_df
        # string to set of string
        self.term_to_docids = term_to_docids
        # string to TextDocument
        self.docid_to_doc = docid_to_doc

    @classmethod
    def from_dir(cls, dir, file_suffix):
        """
        creates DocumentCollection objects from files with suffix file_suffix in dir
        """
        files = [(os.path.abspath(dir) + "/" + f) for f in os.listdir(dir) if f.endswith(file_suffix)]
        docs = [TextDocument.from_file(f) for f in files]
        return cls.from_document_list(docs)

    @classmethod
    def from_document_list(cls, docs):
        """ creates DocumentCollection objects from a list of documents(docs)
        """
        term_to_df = defaultdict(int)
        term_to_docids = defaultdict(set)
        docid_to_doc = dict()
        for doc in docs:
            docid_to_doc[doc.id] = doc
            for token in doc.token_counts.keys():
                term_to_df[token] += 1
                term_to_docids[token].add(doc.id)
        return cls(term_to_df, term_to_docids, docid_to_doc)

    def docs_with_all_tokens(self, tokens):
        """
        Gibt eine Liste mit doc_ids zurück, welche alle tokens beinhalten, bzw. welche mindestens ein token beinhalten
        (nach Bearbeitung)
        """
        docids_for_each_token = [self.term_to_docids[token] for token in tokens]  # Liste mit sets der doc_ids
        docids = set.intersection(*docids_for_each_token)  # union?   Schnittmenge der sets
        if len(docids) == 0:
            docids1 = docids_for_each_token[0]
            return [self.docid_to_doc[id] for id in docids1]  # docs mit zumindest einem token
        else:
            return [self.docid_to_doc[id] for id in docids]  # docs mit allen token

    def tfidf(self, counts):
        """ returns a dictionary mapping all tokens to their tf-idfs
        """
        N = len(self.docid_to_doc)
        return {tok: tf * math.log(N / self.term_to_df[tok]) for tok, tf in counts.items() if tok in self.term_to_df}

    def cosine_similarity(self, docA, docB):
        """
        Berechnet den Cosinus zwischen 2 Dokumenten
        """
        weightedA = self.tfidf(docA.token_counts)  # token_counts ist term_to_tf
        weightedB = self.tfidf(docB.token_counts)
        dotAB = dot(weightedA, weightedB)
        normA = math.sqrt(dot(weightedA, weightedA))
        normB = math.sqrt(dot(weightedB, weightedB))

        if dotAB == 0:
            return 0
        else:
            return dotAB / (normA * normB)

class SearchEngine:
    def __init__(self, doc_collection):
        """ creates SearchEngine object with a class object of DocumentCollection
        """
        self.doc_collection = doc_collection

    def ranked_documents(self, query):
        """ creates a TextDocument object query with text = query, docs includes all documents with all tokens in query, docs_sims returns a list of cosine similarities, which in the end will be sorted and returned
        """
        query_doc = TextDocument(query)
        query_tokens = query_doc.token_counts.keys()
        docs = self.doc_collection.docs_with_all_tokens(query_tokens)
        docs_sims = [(doc, self.doc_collection.cosine_similarity(query_doc, doc)) for doc in docs]
        return sorted(docs_sims, key=lambda x: -x[1])

    def snippets(self, query, document, window=50):
        """ search for each token in query, return all contexts
        """
        tokens = normalized_tokens(query)
        token_set = {i for i in tokens}
        text = document.text
        for token in token_set:
            start = text.lower().find(token.lower())
            if -1 == start:
                continue
            end = start + len(token)
            left = "..." + text[start - window:start]
            middle = "[" + text[start: end] + "]"
            right = text[end:end + window] + "..."
            yield left + middle + right
