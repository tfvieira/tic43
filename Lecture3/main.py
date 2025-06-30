import spacy

if __name__ == "__main__":
    SPACY_MODEL = "en_core_web_sm"
    TEXT = "Contact John Doe at john.doe@email.com for details on project Alpha. The lead developer is Jane Smith."

    nlp = spacy.load(SPACY_MODEL)

    doc = nlp(TEXT)

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            TEXT = TEXT.replace(ent.text, "[REDACTED_NAME]")

    for token in doc:
        if token.like_email:
            TEXT = TEXT.replace(token.text, "[REDACTED_EMAIL]")

    print(TEXT)
