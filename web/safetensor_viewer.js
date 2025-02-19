import { app } from "../../scripts/app.js";

var previous_model = '';

app.registerExtension({
    name: "Comfy.SafetensorViewer",
    async setup() {
        function messageHandler(event) { 
			//alert(event.detail.files); 
			// console.log('EVENT FIRE');
			// console.log(event.detail);
			let node_id = event.detail.node;
			let metadata_str = event.detail.metadata;
			let tensor_info = event.detail.tensor_info;
			// console.log(' ------------ ');
			
			// Find all nodes of this type
            const nodes = app.graph._nodes.filter(n => n.type === node_id);
			// console.log(nodes);
			// console.log(app.graph._nodes);
			
			let widget_name = "notes";
            
            for (const node of nodes) {
                // Find the file widget
				// console.log("NODE:");
				// console.log(node);
                const widget = node.widgets.find(w => w.name === widget_name);
				// console.log(node.widgets);
                if (widget) {
					// console.log("WIDGET FOUND");
                    widget.value = "META:\n" + metadata_str + "\n\nTENSORS:\n" + tensor_info; 
                    //widget.callback(widget.value);
                }
            }
		}

        app.api.addEventListener("SafetensorViewer.update_files", messageHandler);		
    }
});