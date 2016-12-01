package nist.oar.id;

import java.util.HashMap;

/**
 * An interface for creating of identifier strings.  
 */
public interface IDMinter {
    /**
     * return an available identifier string.  
     * 
     * It is an implementation detail as to what portion of the eventual 
     * identifier this string will represent, e.g. whether it includes a 
     * namespace.  
     */
    public String mint(HashMap<String, Object> data = null);

    /**
     * return true if the given identifier string is a recognized one that 
     * has been previously issued.
     */
    public boolean issued(String id);

    /**
     * return the data associated with the given ID.  Null is returned if 
     * no data was associated with the ID when it was minted (or data 
     * association is not supported).  
     */
    public HashMap<String, Object> dataFor(String id);

}
