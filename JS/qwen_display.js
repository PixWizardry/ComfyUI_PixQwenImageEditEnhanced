import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "PixQwenImageEditEnhanced.display",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData?.name !== "PixQwenImageEditEnhanced") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            onNodeCreated?.apply(this, arguments);
            
            this.widgets ??= [];
            let w = this.widgets.find(w => w.name === "token_info");
            
            if (!w) {
                w = {
                    name: "token_info",
                    type: "display",
                    value: "Waiting for generation...",
                    options: {},
                    // Define a computed height property so we can resize dynamically
                    computedHeight: 30,

                    draw: function(ctx, node, widget_width, y, widget_height) {
                        const margin = 10;
                        const text = this.value || "";
                        
                        // 1. Text Setup
                        ctx.font = "12px monospace";
                        ctx.textAlign = "left";
                        ctx.textBaseline = "top"; // Easier for multi-line
                        
                        // 2. Word Wrap Logic
                        const maxWidth = widget_width - (margin * 2);
                        const words = text.split(" ");
                        const lines = [];
                        let currentLine = words[0];

                        for (let i = 1; i < words.length; i++) {
                            const word = words[i];
                            const width = ctx.measureText(currentLine + " " + word).width;
                            if (width < maxWidth) {
                                currentLine += " " + word;
                            } else {
                                lines.push(currentLine);
                                currentLine = word;
                            }
                        }
                        lines.push(currentLine);

                        // 3. Calculate Dynamic Height
                        const lineHeight = 16;
                        const totalTextHeight = lines.length * lineHeight;
                        // Add padding (top + bottom)
                        const finalHeight = totalTextHeight + 14; 

                        // Update our internal height for the next computeSize call
                        this.computedHeight = finalHeight;

                        // 4. Draw Background
                        ctx.fillStyle = "rgba(0, 0, 0, 0.3)";
                        // Draw the box based on calculated height
                        ctx.fillRect(margin, y, widget_width - (margin * 2), finalHeight);
                        
                        // 5. Draw Lines
                        ctx.fillStyle = "#aaaaff"; // Light blue text
                        for (let i = 0; i < lines.length; i++) {
                            ctx.fillText(lines[i], margin + 5, y + 7 + (i * lineHeight));
                        }
                        
                        // Return the Y position where the NEXT widget should start
                        return y + finalHeight + 5; // +5 for spacing
                    },
                    
                    computeSize: function(width) {
                        // Use the height we calculated during the draw phase
                        return [width, this.computedHeight || 30]; 
                    },
                    
                    mouse: function() { return false; }
                };
                
                this.widgets.push(w);
            }
        };

        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function(message) {
            onExecuted?.apply(this, arguments);
            
            if (this.widgets) {
                const w = this.widgets.find(w => w.name === "token_info");
                if (w) {
                    const text = Array.isArray(message?.text) ? message.text.join("") : (message?.text || "");
                    w.value = text;
                    
                    // Force a resize calculation
                    this.onResize?.(this.size);
                    this.setDirtyCanvas(true, true);
                }
            }
        };
    },
});
