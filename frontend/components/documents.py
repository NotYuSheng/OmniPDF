import streamlit as st


def get_document_names():
    return [data["uploaded_filename"] for data in st.session_state.processed_data.values()]


def get_document_ids():
    return st.session_state.processed_data.keys()


def document_multiselect_with_expander():
    document_multiselect = DocumentMultiSelect()
    doc_names = get_document_names()
    doc_ids = get_document_ids()
    expander_list = []
    for doc_name, doc_id in zip(doc_names, doc_ids):
        expander_list.append(DocumentExpander(doc_id, doc_name, document_multiselect))
    return expander_list

class DocumentMultiSelect():
    def __init__(self):
        # Initialize expander states for all documents
        self.doc_names = get_document_names()

        # Initialize expander states for new documents
        for doc_name in self.doc_names:
            if doc_name not in st.session_state.expander_states:
                st.session_state.expander_states[doc_name] = True

    def __contains__(self, item):
        return True  # All documents are always included


class DocumentExpander():
    def __init__(self, doc_id: str, doc_name: str, doc_multiselect: DocumentMultiSelect):
        self.doc_id = doc_id
        self.doc_name = doc_name
        self.expander = st.expander(
                        label=f"**{doc_name}**",
                        expanded=st.session_state.expander_states.get(
                            doc_name, True
                        ),
                    )
        self.status = None
        
        # Update expander state and multiselect when expander is toggled
        if not self.expander:  # expander is closed
            st.session_state.expander_states[doc_name] = (
                False
            )
        else:  # expander is open
            st.session_state.expander_states[doc_name] = (
                True
            )
        
    def __enter__(self):
        self.expander.__enter__()
        self.status = st.empty()

    def __exit__(self, *exc_details):
        self.expander.__exit__(*exc_details)