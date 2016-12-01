package nist.oar.id;

import java.util.HashMap;

/**
 * An interface for storing identifier strings that have been issued already.
 *
 * This class is expected to be used within a IDMinter implementation.  New
 * IDs are reserved from further use by calling registerID().  The IDMinter 
 * can then called issued() with a proposed ID string to determine if it has 
 * already been issued.  
 */
public interface IDRegistry {

    /**
     * register the given ID to reserve it from further use.  
     *
     * An implementation chooses whether to support the storage of data along
     * with the identifier as well as what data to expect.
     *
     * @param id      the ID to be reserved
     * @param data    any data to store with the identifier.
     * @throws IDReservedException  if the id has already exists in storage.
     */
    public void registerID(String id, HashMap<String, Object> data = null);

    /**
     * return true if the given ID has already been registered
     *
     * @param id    the identifier string to check
     */
    public boolean registered(String id);

}
