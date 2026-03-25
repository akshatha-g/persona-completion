# Overview Tab: Network Visualization Plan

## Goal

Create an interactive network graph that visually shows:
1. **Documents** as source nodes
2. **Personas** (people) as central nodes
3. **Detected PIIs** as attribute nodes connected to personas
4. **Evolution over time** as more documents are processed

## Visual Concept

```
    [Doc 001] ──────┐
                    │
    [Doc 002] ──────┼──→ [Kathleen Gregory] ──→ [email]
                    │           │              [phone]
    [Doc 003] ──────┘           │              [employer]
                                │
                                └──→ [First Name]
                                     [Last Name]
                                     [Nationality]
```

## Library Options

| Library | Pros | Cons | Docs |
|---------|------|------|------|
| **vis.js Network** | Simple API, dynamic updates, physics engine | Less customizable | https://visjs.github.io/vis-network/docs/network/ |
| **Cytoscape.js** | Feature-rich, layouts, analysis | Steeper learning curve | https://js.cytoscape.org/ |
| **Sigma.js** | WebGL, handles large graphs | More complex setup | https://www.sigmajs.org/ |
| **D3.js Force** | Full control, beautiful | Most complex | https://d3js.org/d3-force |

**Recommendation**: vis.js Network for simplicity and dynamic data support.

## Data Structure

### Nodes
```javascript
nodes = [
    // Documents (type: 'document')
    { id: 'doc_001', label: 'Doc 001', group: 'document' },
    { id: 'doc_002', label: 'Doc 002', group: 'document' },

    // Personas (type: 'persona')
    { id: 'persona_abc', label: 'Kathleen Gregory', group: 'persona' },

    // PIIs (type: 'pii')
    { id: 'pii_email', label: 'Email', group: 'pii' },
    { id: 'pii_phone', label: 'Phone', group: 'pii' },
]
```

### Edges
```javascript
edges = [
    // Document → Persona (discovered in)
    { from: 'doc_001', to: 'persona_abc' },
    { from: 'doc_002', to: 'persona_abc' },

    // Persona → PII (has attribute)
    { from: 'persona_abc', to: 'pii_email' },
    { from: 'persona_abc', to: 'pii_phone' },
]
```

## Node Styling

| Node Type | Shape | Color | Size |
|-----------|-------|-------|------|
| Document | square | gray (#9E9E9E) | small |
| Persona | circle | blue (#2196F3) | large |
| PII (detected) | dot | green (#4CAF50) | medium |
| PII (missing) | dot | light gray (#E0E0E0) | small |

## Features to Implement

### Phase 1: Static Network
- [ ] Load vis.js library via CDN
- [ ] Build nodes/edges from snapshot data
- [ ] Style nodes by type (document, persona, pii)
- [ ] Basic layout (hierarchical or force-directed)

### Phase 2: Interactive
- [ ] Click on persona → highlight connected docs and PIIs
- [ ] Hover tooltips with details
- [ ] Zoom and pan

### Phase 3: Timeline Animation
- [ ] Slider to select snapshot
- [ ] Animate network as documents are added
- [ ] Show PIIs appearing over time

## Implementation Steps

1. **Add vis.js CDN** to `web/index.html`
   ```html
   <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
   ```

2. **Create container** in Overview tab
   ```html
   <div id="network-container" style="height: 500px;"></div>
   ```

3. **Build graph data** from snapshot
   ```javascript
   function buildNetworkData(snapshot) {
       const nodes = [];
       const edges = [];

       for (const [personaId, profile] of Object.entries(snapshot.profiles)) {
           // Add persona node
           nodes.push({ id: personaId, label: profile.meta.label, group: 'persona' });

           // Add document nodes and edges
           for (const docId of profile.meta.source_documents) {
               if (!nodes.find(n => n.id === docId)) {
                   nodes.push({ id: docId, label: docId, group: 'document' });
               }
               edges.push({ from: docId, to: personaId });
           }

           // Add PII nodes and edges
           for (const pii of profile.detected_piis) {
               const piiNodeId = `${personaId}_${pii}`;
               nodes.push({ id: piiNodeId, label: pii, group: 'pii' });
               edges.push({ from: personaId, to: piiNodeId });
           }
       }

       return { nodes, edges };
   }
   ```

4. **Render network**
   ```javascript
   function renderNetwork(data) {
       const container = document.getElementById('network-container');
       const options = {
           groups: {
               document: { shape: 'square', color: '#9E9E9E' },
               persona: { shape: 'circle', color: '#2196F3', size: 30 },
               pii: { shape: 'dot', color: '#4CAF50' }
           },
           layout: {
               hierarchical: {
                   direction: 'LR',
                   sortMethod: 'directed'
               }
           }
       };
       new vis.Network(container, data, options);
   }
   ```

## Questions to Resolve

1. **Scale**: With 756 documents and 20 personas, should we:
   - Show all documents? (cluttered)
   - Sample documents? (e.g., first 5 per persona)
   - Collapse documents into a count node?

2. **PII grouping**: Show individual PIIs or group by category?

3. **Layout**: Hierarchical (docs → personas → piis) or force-directed?

## Next Steps

1. User confirms approach
2. Implement Phase 1 (static network)
3. Get feedback
4. Iterate
