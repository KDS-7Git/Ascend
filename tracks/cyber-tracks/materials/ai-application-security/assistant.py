"""Deterministic application-boundary fixture. No model or paid API is used."""
DOCS={"public":{"owner":None,"text":"Public training note"},
      "alice-note":{"owner":"alice","text":"Synthetic Alice note"},
      "bob-note":{"owner":"bob","text":"Synthetic Bob note"}}
def retrieve(user, doc_id):
    # Exercise: enforce document ownership BEFORE returning text to any model.
    return DOCS[doc_id]["text"]
def mock_model(document):
    return {"action":"read","document":"bob-note"} if "REQUEST_OTHER" in document else {"action":"answer","text":document}
def dispatch(user, output):
    # Exercise: validate schema, action and ownership independently of generated text.
    if output["action"]=="read": return retrieve(user,output["document"])
    return output["text"]
if __name__ == "__main__":
    print("benign",dispatch("alice",mock_model("Public training note")))
    print("instruction-like text",dispatch("alice",mock_model("REQUEST_OTHER")))
