import {
  AutocompleteInput,
  initAutocompleteInput
} from "./components/AutocompleteInput";

export { AutocompleteInput, initAutocompleteInput };

function initInputs(node) {
  const autocompleteInputNodes = node.querySelectorAll(
    "[data-autocomplete-input]"
  );
  autocompleteInputNodes.forEach(initAutocompleteInput);
}

let mutationObserver = new MutationObserver(function(mutations) {
  mutations.forEach(function(mutation) {
    initInputs(mutation.target);
  });
});

document.addEventListener("DOMContentLoaded", () => {
  initInputs(document);
  const panels = document.querySelectorAll(".object");

  panels.forEach(function(panel) {
    mutationObserver.observe(panel, {
      subtree: true,
      childList: true
    });
  });
});
