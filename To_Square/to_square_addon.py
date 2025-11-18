bl_info = {
    "name" : "Square Addon",
    "author" : "Andre @ojowaa",
    "version" : (1, 0, 0),
    "blender" : (4, 2),
    "location" : "Edge",
    "category" : "Mesh",
}

import bpy
import bmesh
import mathutils
import math
from numpy import roll


class To_Square_Addon(bpy.types.Operator):
    """MY ADDON TOOLTIP"""
    bl_idname = "edge.to_square"
    bl_label = "Square"
    bl_options = {'REGISTER', 'UNDO'}
    
    flip_prop: bpy.props.BoolProperty(name="Flip", default=True)
    rotation_prop: bpy.props.FloatProperty(name="Rotation", default=0)
    width_prop: bpy.props.FloatProperty(name="Width", default=1)
    auto_width_prop: bpy.props.BoolProperty(name="Auto Width", default=True)
    offset_prop: bpy.props.IntProperty(name="Offset", default=0)
    norm_prop: bpy.props.BoolProperty(name="Lock Norm", default=False)
    x_prop: bpy.props.BoolProperty(name="Lock X", default=False)
    y_prop: bpy.props.BoolProperty(name="Lock Y", default=False)
    z_prop: bpy.props.BoolProperty(name="Lock Z", default=False)
    
    
    def draw(self, context):
        layout = self.layout

        layout.prop(self, "rotation_prop", text="Rotation")
        layout.prop(self, "offset_prop", text="Offset")
        layout.prop(self, "flip_prop", text="Flip")
        layout.prop(self, "auto_width_prop", text="Auto Width")
        if not self.auto_width_prop:
            layout.prop(self, "width_prop", text="Width")
        
        
        
        # Create checkboxes for each property
        layout.separator()

        row = layout.row()
        row.label(text="Lock Movement")

        row = layout.row()
        if self.norm_prop:
            row.prop(self, "norm_prop", text="Lock Normal Axis", icon='LOCKED')
        else:
            row.prop(self, "norm_prop", text="Lock Normal Axis", icon='UNLOCKED')

        if not self.norm_prop:
            row = layout.row()
            if self.x_prop:
                row.prop(self, "x_prop", text="Lock X", icon='LOCKED')
            else:
                row.prop(self, "x_prop", text="Lock X", icon='UNLOCKED')
            if self.y_prop:
                row.prop(self, "y_prop", text="Lock Y", icon='LOCKED')
            else:
                row.prop(self, "y_prop", text="Lock Y", icon='UNLOCKED')
            if self.z_prop:
                row.prop(self, "z_prop", text="Lock Z", icon='LOCKED')
            else:
                row.prop(self, "z_prop", text="Lock Z", icon='UNLOCKED')

    
    def execute(self, context): 

        #inputs
        flip=self.flip_prop
        rotation=self.rotation_prop
        width=self.width_prop
        offset=self.offset_prop
        lock_norm=self.norm_prop
        lock_x=self.x_prop
        lock_y=self.y_prop
        lock_z=self.z_prop

        def avg_norm(pts):
            total=mathutils.Vector((0.0, 0.0, 0.0))
            count = len(pts)
            for i in range(count):
                pos1 = pts[(i-1)%count].co
                pos2 = pts[(i)%count].co
                pos3 = pts[(i+1)%count].co
        #        total += (pos1-pos2).cross(pos3-pos2).normalized()
                total += (pos1-pos2).cross(pos3-pos2)
            total = total/count
            return total.normalized()

        def avg_pos(pts):
            total=mathutils.Vector((0.0, 0.0, 0.0))
            count = len(pts)
            for i in range(count):
                total += pts[(i)].co
            total = total/count
            return total
        
        def avg_width(pts, pos):
            temp = 0.0
            count = len(pts)
            for i in range(count):
                temp += (pts[i].co-pos).length
            temp = temp/count
            return temp*2

        obj = bpy.context.active_object
        #selected_verts = list(filter(lambda v: v.select, obj.data.vertices))

        bm = bmesh.from_edit_mesh(obj.data)
#        selected_verts = list(filter(lambda v: v.select, bm.verts))
        selected_verts = [v for v in bm.verts if v.select]
        
        if not selected_verts:
            self.report({'ERROR'}, "No vertices selected.")
            return {'CANCELLED'}
        
        
        # selected verts
        selected_verts = [v for v in bm.verts if v.select]

               # Build adjacency among selected verts
        adj = {}
        for v in selected_verts:
            neigh = [e.other_vert(v) for e in v.link_edges if e.other_vert(v) in selected_verts]
            adj[v] = neigh
            if len(neigh) > 2:
                # More than 2 (or less than 2) means the ring isn't clean → cancel
                self.report({'ERROR'}, "Selection is unclear.")
                return {'CANCELLED'}

        # Walk the ring
        ordered = []
        visited = set()

        current = selected_verts[0]
        prev = None

        while True:
            ordered.append(current)
            visited.add(current)

            n1, n2 = adj[current]
            nxt = n1 if n1 != prev else n2

            prev, current = current, nxt

            if current in visited:
                break

        # Remove duplicated start vertex
        selected_verts = ordered

        count = len(selected_verts)
        avg_pos = avg_pos(selected_verts)
        avg_norm = avg_norm(selected_verts)

        if self.auto_width_prop:
            width=avg_width(selected_verts, avg_pos)

        selected_verts = roll(selected_verts,offset)
        backup_verts = selected_verts

        y_count = math.floor(count/4)
        for i in range(y_count):
            edge_len = width/y_count
            selected_verts[i].co = mathutils.Vector((edge_len*i, 0.0, 0.0))
            selected_verts[y_count+i].co = mathutils.Vector((width, edge_len*i, 0.0))
            selected_verts[y_count*2+i].co = mathutils.Vector((width-(edge_len*i), width, 0.0))
            
        r_count = count-(y_count*3)
        for i in range(r_count):
            edge_len = width/r_count
            selected_verts[y_count*3+i].co = mathutils.Vector((0.0, width-(edge_len*i), 0.0))


        eul = mathutils.Euler((0.0, flip*math.pi, 0.0), 'XYZ')
        eul.rotate_axis('Z', math.radians(rotation))
        mat_rot = eul.to_matrix()

        rotation_matrix = avg_norm.to_track_quat('Z', 'Y').to_matrix().to_4x4()


        bmesh.ops.translate(
            bm,
            verts=selected_verts,
            vec=(width*-0.5,width*-0.5,0.0))
        bmesh.ops.rotate(
            bm,
            verts=selected_verts,
            cent=(0.0, 0.0, 0.0),
            matrix=mat_rot)
        bmesh.ops.rotate(
            bm,
            verts=selected_verts,
            cent=(0.0, 0.0, 0.0),
            matrix=rotation_matrix)
        bmesh.ops.translate(
            bm,
            verts=selected_verts,
            vec=avg_pos)

        for i in range(count):
            delta_pos = selected_verts[i].co-backup_verts[i].co
            if self.norm_prop and delta_pos.length != 0:
                selected_verts[i].co = avg_norm.dot(delta_pos)/delta_pos.length
            else:
                selected_verts[i].co = mathutils.Vector((
                    backup_verts[i].co.x if lock_x else selected_verts[i].co.x,
                    backup_verts[i].co.y if lock_y else selected_verts[i].co.y,
                    backup_verts[i].co.z if lock_z else selected_verts[i].co.z
                ))

        bmesh.update_edit_mesh(obj.data)
        bm.free()

        return {'FINISHED'} 

def menu_func(self, context):
    self.layout.operator(To_Square_Addon.bl_idname)
            
def register():
    bpy.utils.register_class(To_Square_Addon)
    bpy.types.VIEW3D_MT_edit_mesh.append(menu_func)
            
def unregister():
    bpy.utils.unregister_class(To_Square_Addon)
    bpy.types.VIEW3D_MT_edit_mesh.remove(menu_func)
            
if __name__ == "__main__":
    register()